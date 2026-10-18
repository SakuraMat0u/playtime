# -*- coding: utf-8 -*-
"""外壳：标题栏 / 侧边栏 / 状态栏 —— 尺寸严格对齐设计稿"""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app import theme
from app.charts import StatusDot, gradient_tile
from app.widgets import Card, NavItem, SectionLabel, WindowButton


class LogoMark(QWidget):
    """18×18 渐变圆角方块"""

    def __init__(self, size=18, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient_tile(p, QRectF(0, 0, self.width(), self.height()),
                      theme.CYAN, theme.PURPLE, self.width() * 0.3)
        p.end()


class TitleBar(QWidget):
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.setFixedHeight(theme.TITLEBAR_H)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 10, 0)
        lay.setSpacing(8)

        lay.addWidget(LogoMark(18), 0, Qt.AlignmentFlag.AlignVCenter)
        title = QLabel("Playtime · 游戏时长统计")
        title.setStyleSheet("color:rgba(20,24,32,0.86);font-size:12px;font-weight:600;")
        lay.addWidget(title, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addStretch(1)

        self.btn_min = WindowButton("min")
        self.btn_max = WindowButton("max")
        self.btn_close = WindowButton("close", hover_bg="rgba(255,77,109,0.85)",
                                      hover_fg="#FFFFFF")
        for b in (self.btn_min, self.btn_max, self.btn_close):
            lay.addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)

        self.btn_min.clicked.connect(self.window.showMinimized)
        self.btn_max.clicked.connect(self.window.toggle_maximize)
        self.btn_close.clicked.connect(self.window.close)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.window.start_drag(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        self.window.do_drag(e.globalPosition().toPoint())

    def mouseReleaseEvent(self, e):
        self.window.end_drag()

    def mouseDoubleClickEvent(self, e):
        self.window.toggle_maximize()


class Sidebar(QWidget):
    NAV = [("library", "游戏库", "gamepad"),
           ("analytics", "统计分析", "chart"), ("settings", "设置", "settings")]

    def __init__(self, on_nav, parent=None):
        super().__init__(parent)
        self.setFixedWidth(theme.SIDEBAR_W)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.on_nav = on_nav
        self.nav_items = {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 16, 14, 16)
        lay.setSpacing(6)

        lay.addWidget(SectionLabel("导航"))
        lay.addSpacing(4)
        for key, text, icon in self.NAV:
            it = NavItem(key, text, icon)
            it.clicked.connect(self.on_nav)
            self.nav_items[key] = it
            lay.addWidget(it)

        lay.addStretch(1)

        # 监控状态卡片
        self.monitor_card = Card()
        mc = QVBoxLayout(self.monitor_card)
        mc.setContentsMargins(14, 12, 14, 12)
        mc.setSpacing(6)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(StatusDot(theme.CYAN, 7))
        t = QLabel("监控运行中")
        t.setStyleSheet(f"color:{theme.TXT_1};font-size:12px;font-weight:600;")
        row.addWidget(t)
        row.addStretch(1)
        mc.addLayout(row)
        self.monitor_sub = QLabel("已收录 0 款游戏")
        self.monitor_sub.setObjectName("card_sub")
        mc.addWidget(self.monitor_sub)
        lay.addWidget(self.monitor_card)

    def set_nav(self, key: str):
        for k, it in self.nav_items.items():
            it.set_active(k == key)

    def set_game_count(self, n: int):
        self.monitor_sub.setText(f"已收录 {n} 款游戏")


class StatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(theme.STATUS_H)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 0, 24, 0)
        self.left = QLabel("监控服务已启动")
        self.left.setObjectName("status")
        self.right = QLabel("数据本地存储")
        self.right.setObjectName("status")
        lay.addWidget(self.left)
        lay.addStretch(1)
        lay.addWidget(self.right)

    def set_left(self, s):
        self.left.setText(s)

    def set_right(self, s):
        self.right.setText(s)
