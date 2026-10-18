# -*- coding: utf-8 -*-
"""Playtime · 游戏时长统计 —— 无边框桌面应用入口"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import hashlib
import os
import sys
import winreg
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFontDatabase, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QMenu, QMessageBox, QStackedWidget,
                               QSystemTrayIcon, QVBoxLayout, QWidget)

from app import storage, theme
from app.charts import AuroraBackdrop, gradient_tile
from app.monitor import Monitor
from app.screens import AnalyticsScreen, LibraryScreen, SettingsScreen
from app.shell import Sidebar, StatusBar, TitleBar
from app.widgets import h_divider, v_divider

APP_NAME = "Playtime"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)          # PyInstaller onefile
    return Path(__file__).resolve().parent


def user_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Playtime"


def load_fonts():
    """加载随包字体（Inter / JetBrains Mono），缺失时自动回退系统字体"""
    d = app_dir() / "assets" / "fonts"
    if not d.is_dir():
        return
    for f in sorted(d.glob("*.ttf")) + sorted(d.glob("*.otf")):
        try:
            QFontDatabase.addApplicationFont(str(f))
        except Exception:
            pass


def make_icon(size=64) -> QIcon:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient_tile(p, QRectF(0, 0, size, size), theme.CYAN, theme.PURPLE, size * 0.28)
    p.setPen(QColor("#030014"))
    p.setFont(theme.ui(size * 0.5, theme.Bold))
    p.drawText(0, 0, size, size, Qt.AlignmentFlag.AlignCenter, "P")
    p.end()
    return QIcon(pm)


def autostart_command() -> str:
    """注册表 Run 项的启动命令：打包版直接是 exe，源码版必须是 python + 脚本路径"""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimized'
    return f'"{sys.executable}" "{Path(__file__).resolve()}" --minimized'


def set_autostart(enabled: bool, command: str):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if enabled:
                winreg.SetValueEx(k, APP_NAME, 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(k, APP_NAME)
                except FileNotFoundError:
                    pass
    except Exception:
        pass


def ensure_single_instance() -> bool:
    """同一数据目录只允许一个实例，避免两个实例互相覆盖数据。

    返回 False 表示已有实例在运行（本进程应退出）。
    """
    name = "Local\\Playtime_" + hashlib.md5(
        os.path.abspath(storage.DATA_DIR).encode("utf-8")).hexdigest()[:10]
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW(None, True, name)
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        ctypes.windll.user32.MessageBoxW(
            0,
            "Playtime 已经在运行了。\n\n同一数据目录只允许一个实例，请在任务栏或托盘找到已有窗口。",
            "Playtime", 0x40)
        return False
    return True  # 句柄不主动释放，随进程退出自动清理


class Ctx:
    """界面与后端之间的共享上下文"""

    def __init__(self):
        self.db = storage.load()
        self.monitor = Monitor(lambda: self.db)
        self.goto = lambda key: None
        self.refresh_all = lambda: None
        self.apply_settings = lambda: None

    def save(self):
        storage.save(self.db)


class MainWindow(QWidget):
    SCREENS = {"library": 0, "analytics": 1, "settings": 2}

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setObjectName("root")
        self.setMinimumSize(1100, 700)
        self.resize(theme.WIN_W, theme.WIN_H)
        self.setWindowTitle("Playtime · 游戏时长统计")
        self.setWindowIcon(make_icon())

        self.ctx = Ctx()
        if storage.LOAD_WARNING:
            QMessageBox.warning(
                self, "数据文件已备份",
                f"原数据文件损坏，无法读取。\n已备份为：\n{storage.LOAD_WARNING}\n\n"
                "程序将从空库开始，修复备份文件后可改回 data.json。")
        self._drag = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.backdrop = AuroraBackdrop(self)
        self.backdrop.resize(self.size())
        self.backdrop.lower()

        self.titlebar = TitleBar(self)
        root.addWidget(self.titlebar)
        root.addWidget(h_divider())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.sidebar = Sidebar(self.goto)
        body.addWidget(self.sidebar)
        body.addWidget(v_divider())

        self.stack = QStackedWidget()
        self.lib = LibraryScreen(self.ctx)
        self.ana = AnalyticsScreen(self.ctx)
        self.cfg = SettingsScreen(self.ctx)
        for s in (self.lib, self.ana, self.cfg):
            self.stack.addWidget(s)
        body.addWidget(self.stack, 1)

        self.ctx.goto = self.goto
        self.ctx.refresh_all = self.refresh_all
        self.ctx.apply_settings = self.apply_settings
        root.addLayout(body, 1)

        root.addWidget(h_divider())
        self.statusbar = StatusBar()
        root.addWidget(self.statusbar)

        # 后端信号
        m = self.ctx.monitor
        m.status.connect(self.statusbar.set_left)
        m.tick.connect(self._on_tick)
        m.session_started.connect(lambda _: self.refresh_all())
        m.session_ended.connect(lambda *_: self.refresh_all())

        self._sync_timer = QTimer(self)
        self._sync_timer.setInterval(1000)
        self._sync_timer.timeout.connect(self._on_second)
        self._sync_timer.start()

        # 托盘
        self.tray = QSystemTrayIcon(make_icon(), self)
        menu = QMenu()
        menu.setStyleSheet(
            "QMenu{background:#14101F;color:#fff;border:1px solid rgba(255,255,255,0.1);"
            "padding:4px;} QMenu::item{padding:6px 22px;border-radius:6px;}"
            "QMenu::item:selected{background:rgba(255,255,255,0.1);}")
        menu.addAction("显示窗口", self.show_normal)
        menu.addSeparator()
        menu.addAction("退出", self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda r: self.show_normal() if r == QSystemTrayIcon.ActivationReason.Trigger else None)
        self.tray.show()

        self.goto("library")
        self.refresh_all()
        self.apply_settings()
        m.start()
        QApplication.instance().aboutToQuit.connect(m.stop)

    # ---------------------------------------------------------------- 导航
    def goto(self, key: str):
        idx = self.SCREENS.get(key, 0)
        self.stack.setCurrentIndex(idx)
        self.sidebar.set_nav(key if key in self.SCREENS else "library")
        self.refresh_all()

    def refresh_all(self):
        self.lib.refresh()
        self.ana.refresh()
        self.cfg.refresh()
        self.sidebar.set_game_count(len(self.ctx.db["games"]))
        self.statusbar.set_right(
            f"数据本地存储 · 上次同步 {datetime.now().strftime('%H:%M')}")

    # ---------------------------------------------------------------- 计时
    def _on_tick(self, _gid, _sec):
        pass

    def _on_second(self):
        self.lib.on_tick()

    # ---------------------------------------------------------------- 设置
    def apply_settings(self):
        s = self.ctx.db["settings"]
        set_autostart(bool(s.get("autostart")), autostart_command())

    # ---------------------------------------------------------------- 窗口控制
    def start_drag(self, pos: QPoint):
        self._drag = pos - self.frameGeometry().topLeft()

    def do_drag(self, pos: QPoint):
        if self._drag is not None:
            self.move(pos - self._drag)

    def end_drag(self):
        self._drag = None

    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def show_normal(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, e):
        if self.ctx.db["settings"].get("minimize_to_tray") and self.tray.isVisible():
            self.hide()
            self.tray.showMessage("Playtime", "已最小化到托盘，后台继续统计",
                                  QSystemTrayIcon.MessageIcon.Information, 2000)
            e.ignore()
            return
        self.quit_app()
        e.accept()

    def quit_app(self):
        self.ctx.monitor.stop()
        self.ctx.save()
        self.tray.hide()
        QApplication.quit()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.backdrop.resize(self.size())


def main():
    if not ensure_single_instance():
        return
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    load_fonts()
    app.setStyleSheet(theme.stylesheet())

    w = MainWindow()
    if "--minimized" in sys.argv:
        w.hide()
    else:
        w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
