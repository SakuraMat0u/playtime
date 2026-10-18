# -*- coding: utf-8 -*-
"""进程监控：轮询已登记游戏的进程，累计会话时长"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import platform
import time
import uuid
from datetime import datetime, timedelta

from PySide6.QtCore import QThread, Signal

from app import storage

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
        self._live: dict[str, str] = {}      # game_id -> 进行中会话在 db 中的记录 id
        self._last_journal: dict[str, int] = {}   # game_id -> 上次落盘的秒数
        self._suppressed: set[str] = set()   # 手动「结束」后暂停自动计时, 直到进程退出
        self._last_diag = 0.0                # 诊断日志节流

    # ---------------------------------------------------------------- 诊断
    def _write_diag(self, tracked: dict[str, str], names: set[str], reason: str):
        """匹配不到进程时，把本次扫描结果写进 userconfig\\monitor.log（20 秒一次，自动截断）。

        用于排查“登记了游戏但状态栏一直显示等待游戏启动”。
        """
        now = time.time()
        if now - self._last_diag < 20:
            return
        self._last_diag = now
        try:
            from pathlib import Path

            path = Path(storage.DATA_DIR) / "monitor.log"
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            known = sorted(set(tracked.values()))
            sample = sorted(names)
            body = [
                f"[{stamp}] reason={reason} tracked={known} scanned={len(sample)}",
                "  names=" + ", ".join(sample[:80]),
                "",
            ]
            with path.open("a", encoding="utf-8") as f:
                f.write("\n".join(body) + "\n")
            if path.stat().st_size > 200_000:
                lines = path.read_text(encoding="utf-8").splitlines()[-400:]
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception:
            pass

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

    # ---------------------------------------------------------------- 落盘
    @staticmethod
    def _record(session_id: str, seconds: int) -> dict:
        now = datetime.now()
        return {
            "id": session_id,
            "start": (now - timedelta(seconds=seconds)).isoformat(timespec="seconds"),
            "end": now.isoformat(timespec="seconds"),
            "seconds": int(seconds),
        }

    def _journal(self, db: dict):
        """把进行中的会话周期性写进 data.json。

        崩溃/强杀最多丢失一个扫描周期（3 秒）的计时，而不是整段会话。
        """
        now = time.time()
        dirty = False
        for gid, a in list(self._active.items()):
            sec = int(a["acc"] + (0 if a["paused"] else now - a["start"]))
            if sec < 5 or self._last_journal.get(gid) == sec:
                continue
            sid = self._live.get(gid)
            if not sid:
                sid = "live_" + uuid.uuid4().hex[:8]
                self._live[gid] = sid
            storage.upsert_session(db, gid, self._record(sid, sec))
            self._last_journal[gid] = sec
            dirty = True
        if dirty:
            storage.save(db)

    def _finalize(self, db: dict, gid: str) -> int:
        """结算一个会话：≥5 秒更新/创建最终记录，否则删除记录。不落盘（调用方批量 save）"""
        a = self._active.get(gid)
        if not a:
            return 0
        sec = int(a["acc"] + (0 if a["paused"] else time.time() - a["start"]))
        sid = self._live.get(gid)
        if sec >= 5:
            if not sid:
                # 从未被周期落盘过（如结束得比扫描周期快）：补一条最终记录
                sid = "live_" + uuid.uuid4().hex[:8]
                self._live[gid] = sid
            storage.upsert_session(db, gid, self._record(sid, sec))
        elif sid:
            storage.remove_session(db, gid, sid)
        return sec

    def _drop(self, gid: str):
        self._active.pop(gid, None)
        self._live.pop(gid, None)
        self._last_journal.pop(gid, None)

    def end_session(self, gid: str) -> int:
        """界面「结束」按钮：立即结算，并在进程退出前不再自动计时"""
        db = self.db_getter()
        sec = 0
        try:
            had_live = gid in self._live
            sec = self._finalize(db, gid)
            if had_live or sec >= 5:
                storage.save(db)
        except Exception:
            pass
        self._drop(gid)
        self._suppressed.add(gid)
        if sec:
            self.session_ended.emit(gid, sec)
        return sec

    def _flush_all(self):
        """把进行中的会话按当前累计时长落盘（退出/刷新时调用）"""
        db = self.db_getter()
        dirty = False
        for gid in list(self._active.keys()):
            if self._finalize(db, gid) or gid in self._live:
                dirty = True
            self._drop(gid)
        if dirty:
            try:
                storage.save(db)
            except Exception:
                pass

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
                   for g in list(db["games"]) if g.get("process")}
        tracked = {k: v for k, v in tracked.items() if v}
        if not tracked and not self._active:
            self.status.emit("监控服务已启动 · 未登记进程")
            return

        names = running_names()
        ended = []

        # 一个都匹配不上时记录一次现场，便于用户反馈“状态栏一直等待游戏启动”
        if tracked and not any(p in names for p in tracked.values()):
            self._write_diag(tracked, names, "empty-scan" if not names else "no-match")

        for gid, proc in tracked.items():
            present = proc in names
            if present and gid not in self._active and gid not in self._suppressed:
                self._active[gid] = {"start": time.time(), "acc": 0.0, "paused": False}
                self.session_started.emit(gid)
            elif not present:
                # 进程已退出：解除手动「结束」的抑制，恢复自动计时
                self._suppressed.discard(gid)
                if gid in self._active:
                    sec = self._finalize(db, gid)
                    if sec or gid in self._live:
                        ended.append((gid, sec))
                    self._drop(gid)

        if ended:
            try:
                storage.save(db)
            except Exception:
                pass
            for gid, sec in ended:
                if sec:
                    self.session_ended.emit(gid, sec)

        # 空闲自动暂停
        if db["settings"].get("idle_pause") and self._active:
            is_idle = idle_seconds() > 60.0 * float(db["settings"].get("idle_minutes", 5))
            for gid, a in self._active.items():
                if is_idle and not a["paused"]:
                    self.pause(gid)
                elif not is_idle and a["paused"]:
                    self.resume(gid)

        # 周期落盘：崩溃/强杀最多丢一个扫描周期
        if self._active:
            try:
                self._journal(db)
            except Exception:
                pass

        for gid in list(self._active.keys()):
            self.tick.emit(gid, self.elapsed(gid))

        n = len(self._active)
        self.status.emit(
            f"监控服务已启动 · 正在追踪 {n} 个进程" if n else "监控服务已启动 · 等待游戏启动")
