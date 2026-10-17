# -*- coding: utf-8 -*-
"""进程监控：轮询已登记游戏的进程，累计会话时长"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import os
import platform
import time
from datetime import datetime

from PySide6.QtCore import QThread, Signal

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None

TH32CS_SNAPPROCESS = 0x00000002
MAX_PATH = 260
# platform.system() 在 Python 3.13 上会走 WMI/COM，只能主线程调用，
# 这里在导入期（主线程）取一次并缓存，避免后台线程里崩溃。
IS_WINDOWS = (platform.system() == "Windows")


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * MAX_PATH),
    ]


_kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
_user32 = ctypes.WinDLL("user32", use_last_error=True)

_kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
_kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
_kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
_kernel32.Process32FirstW.restype = wintypes.BOOL
_kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
_kernel32.Process32NextW.restype = wintypes.BOOL
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL
_kernel32.GetTickCount.argtypes = []
_kernel32.GetTickCount.restype = wintypes.DWORD


def _names_win32() -> set[str]:
    """用 Toolhelp32 快照枚举进程名（纯 ctypes，避免第三方扩展崩溃）"""
    names: set[str] = set()
    snap = None
    try:
        snap = _kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if not snap or snap == ctypes.c_void_p(-1).value:
            return names
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = _kernel32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            names.add(entry.szExeFile.lower())
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
            ok = _kernel32.Process32NextW(snap, ctypes.byref(entry))
    except Exception:
        pass
    finally:
        if snap:
            try:
                _kernel32.CloseHandle(snap)
            except Exception:
                pass
    return names


def running_names() -> set[str]:
    """当前系统中正在运行的进程名（小写集合）"""
    if IS_WINDOWS:
        names = _names_win32()
        if names:
            return names
    if psutil is not None:                       # 非 Windows 或快照失败时兜底
        try:
            return {p.info["name"].lower() for p in psutil.process_iter(["name"])
                    if p.info.get("name")}
        except Exception:
            pass
    return set()


def idle_seconds() -> float:
    """系统空闲秒数（Windows 用 GetLastInputInfo）"""
    if not IS_WINDOWS:
        return 0.0

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    _user32.GetLastInputInfo.argtypes = [ctypes.POINTER(LASTINPUTINFO)]
    _user32.GetLastInputInfo.restype = wintypes.BOOL

    li = LASTINPUTINFO()
    li.cbSize = ctypes.sizeof(LASTINPUTINFO)
    try:
        if _user32.GetLastInputInfo(ctypes.byref(li)):
            elapsed = _kernel32.GetTickCount() - li.dwTime
            return max(0.0, elapsed / 1000.0)
    except Exception:
        pass
    return 0.0


class Monitor(QThread):
    """后台轮询线程"""

    session_started = Signal(str)          # game_id
    session_ended = Signal(str, int)       # game_id, seconds
    tick = Signal(str, int)                # game_id, 本次会话已进行秒数
    status = Signal(str)                   # 状态栏文案

    INTERVAL = 3.0

    def __init__(self, db_getter, parent=None):
        super().__init__(parent)
        self.db_getter = db_getter      # callable() -> db dict
        self._running = True
        self._active: dict[str, dict] = {}   # game_id -> {start, acc, paused}
        self._last_seen: set[str] = set()

    def stop(self):
        self._running = False
        self.wait(4000)

    def active_ids(self) -> set[str]:
        return set(self._active.keys())

    def elapsed(self, game_id: str) -> int:
        a = self._active.get(game_id)
        if not a:
            return 0
        return int(a["acc"] + (0 if a["paused"] else time.time() - a["start"]))

    def is_paused(self, game_id: str) -> bool:
        a = self._active.get(game_id)
        return bool(a and a["paused"])

    def pause(self, game_id: str):
        a = self._active.get(game_id)
        if a and not a["paused"]:
            a["acc"] += time.time() - a["start"]
            a["paused"] = True

    def resume(self, game_id: str):
        a = self._active.get(game_id)
        if a and a["paused"]:
            a["start"] = time.time()
            a["paused"] = False

    def _flush_all(self):
        """把进行中的会话按当前累计时长落盘（退出/刷新时调用）"""
        db = self.db_getter()
        for gid, a in self._active.items():
            sec = int(a["acc"] + (0 if a["paused"] else time.time() - a["start"]))
            if sec >= 5:
                from app import storage
                storage.add_session(db, gid, sec)
                storage.save(db)

    def run(self):
        while self._running:
            try:
                self._scan()
            except Exception:
                pass
            for _ in range(int(self.INTERVAL * 4)):
                if not self._running:
                    break
                self.msleep(250)
        self._flush_all()

    def _scan(self):
        db = self.db_getter()
        tracked = {g["id"]: (g.get("process") or "").strip().lower()
                   for g in db["games"] if g.get("process")}
        tracked = {k: v for k, v in tracked.items() if v}
        if not tracked and not self._active:
            self.status.emit("监控服务已启动 · 未登记进程")
            return

        names = running_names()

        # 开始
        for gid, proc in tracked.items():
            present = proc in names
            if present and gid not in self._active:
                self._active[gid] = {"start": time.time(), "acc": 0.0, "paused": False}
                self.session_started.emit(gid)
            elif not present and gid in self._active:
                a = self._active.pop(gid)
                sec = int(a["acc"] + (0 if a["paused"] else time.time() - a["start"]))
                if sec >= 5:
                    from app import storage
                    storage.add_session(db, gid, sec)
                    storage.save(db)
                    self.session_ended.emit(gid, sec)

        # 空闲自动暂停
        if db["settings"].get("idle_pause") and self._active:
            is_idle = idle_seconds() > 60.0 * float(db["settings"].get("idle_minutes", 5))
            for gid, a in self._active.items():
                if is_idle and not a["paused"]:
                    self.pause(gid)
                elif not is_idle and a["paused"]:
                    self.resume(gid)

        for gid in list(self._active.keys()):
            self.tick.emit(gid, self.elapsed(gid))

        n = len(self._active)
        self.status.emit(
            f"监控服务已启动 · 正在追踪 {n} 个进程" if n else "监控服务已启动 · 等待游戏启动")


def derive_process(exe_path: str) -> str:
    return os.path.basename(exe_path or "")
