# -*- coding: utf-8 -*-
"""本地数据存储：优先 <程序目录>\\userconfig\\data.json（便携），不可写时回退
%LOCALAPPDATA%\\Playtime\\data.json（也可导出 CSV）"""
from __future__ import annotations

import csv
import json
import os
import random
import shutil
import sys
import threading
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path


def _legacy_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "Playtime"


def _cli_data_dir() -> Path | None:
    """启动器传入的数据目录：--data-dir <路径> 或 --data-dir=<路径>"""
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a == "--data-dir" and i + 1 < len(argv):
            return Path(argv[i + 1])
        if a.startswith("--data-dir="):
            return Path(a.split("=", 1)[1])
    return None


def _writable(d: Path) -> Path | None:
    try:
        d.mkdir(parents=True, exist_ok=True)
        probe = d / ".writable"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return d
    except Exception:
        return None


def _portable_dir() -> Path | None:
    """便携模式：优先启动器指定的目录，其次 exe 同级的 userconfig\\

    冻结后才启用；从源码运行时用 %LOCALAPPDATA%，避免污染仓库目录。
    """
    explicit = _cli_data_dir()
    if explicit is not None:
        d = _writable(explicit)
        if d is not None:
            return d
    if not getattr(sys, "frozen", False):
        return None
    return _writable(Path(sys.executable).resolve().parent / "userconfig")


def _resolve_data_dir() -> Path:
    """便携目录优先；首次运行时把旧位置的数据迁移过来"""
    portable = _portable_dir()
    if portable is None:
        return _legacy_dir()
    target = portable / "data.json"
    legacy = _legacy_dir() / "data.json"
    if not target.exists() and legacy.is_file():
        try:
            shutil.copyfile(legacy, target)
        except Exception:
            pass
    return portable


DATA_DIR = str(_resolve_data_dir())
DATA_FILE = os.path.join(DATA_DIR, "data.json")

# 数据文件损坏时的备份路径（供界面提示）；None 表示本次加载正常
LOAD_WARNING: str | None = None

DEFAULT_SETTINGS = {
    "autostart": False,
    "minimize_to_tray": True,
    "idle_pause": True,
    "idle_minutes": 5,
    "week_goal_hours": 40,
}

_NOW = datetime.now()

# ------------------------------------------------------------------ 示例种子数据
# 与设计稿展示的数值一致（总时长 1,284.6h / 本周 38.2h / 最长单次 6.4h）
# 可在「设置 → 数据管理 → 清空数据」中移除
# (名称, 可执行文件, 进程名, 总时长h, [(N天前, 时长h)])
_WEEK_SESSIONS = [
    # 本周合计 38.2h：六 5.3 / 五 5.9 / 四 8.4 / 三 6.2 / 二 7.8 / 一 8.6
    ("赛博朋克 2077", "Cyberpunk2077.exe", "Cyberpunk2077.exe", 338.5,
     [(0, 2.4), (1, 3.1), (2, 2.8), (3, 2.0), (4, 1.4), (9, 6.4)]),   # 9 天前那次即「最长单次」
    ("艾尔登法环", "eldenring.exe", "eldenring.exe", 212.0, [(1, 2.8), (3, 3.6)]),
    ("荒野大镖客 2", "RDR2.exe", "RDR2.exe", 186.3, [(2, 3.4), (4, 2.7)]),
    ("文明 VI", "CivilizationVI.exe", "CivilizationVI.exe", 154.7, [(3, 1.5), (5, 4.6)]),
    ("反恐精英 2", "cs2.exe", "cs2.exe", 128.9, [(2, 2.2), (4, 1.6)]),
    ("巫师 3", "witcher3.exe", "witcher3.exe", 96.4, [(5, 4.1)]),
    ("只狼：影逝二度", "sekiro.exe", "sekiro.exe", 51.2, [(6, 1.8)]),
    ("鬼泣 5", "DevilMayCry5.exe", "DevilMayCry5.exe", 38.6, [(7, 2.2)]),
    ("无主之地 3", "Borderlands3.exe", "Borderlands3.exe", 30.4, [(8, 1.4)]),
    ("星际拓荒", "OuterWilds.exe", "OuterWilds.exe", 21.8, [(10, 1.1)]),
    ("空洞骑士", "hollow_knight.exe", "hollow_knight.exe", 14.6, [(11, 0.9)]),
    ("星露谷物语", "Stardew Valley.exe", "StardewValley.exe", 11.2, [(12, 0.7)]),
]


def _history_sessions(idx: int, budget_h: float, days: int = 17) -> list[tuple[int, float]]:
    """确定性地生成「本周之前」的历史会话，总量受预算约束"""
    rng = random.Random(1000 + idx * 37)
    cap = min(budget_h * 0.35, 24.0)
    out, total = [], 0.0
    for d in range(7, days + 7):
        if total >= cap:
            break
        if rng.random() < 0.75:
            h = round(rng.uniform(0.5, 2.2), 2)
            if total + h > cap:
                h = round(cap - total, 2)
            if h < 0.3:
                break
            out.append((d, h))
            total += h
    return out


def _seed_db() -> dict:
    games = []
    for idx, (name, exe, proc, hours, week) in enumerate(_WEEK_SESSIONS):
        gid = uuid.uuid4().hex[:10]
        week_h = sum(h for _, h in week)
        raw = list(week) + _history_sessions(idx, max(hours - week_h, 0.0))

        sess, used = [], 0
        for days_ago, h in raw:
            start = _NOW - timedelta(days=days_ago, hours=1, minutes=(idx * 13) % 55)
            sec = int(h * 3600)
            sess.append({
                "id": uuid.uuid4().hex[:8],
                "start": start.isoformat(timespec="seconds"),
                "end": (start + timedelta(seconds=sec)).isoformat(timespec="seconds"),
                "seconds": sec,
            })
            used += sec

        # 差额作为历史累计基线，保证「总游戏时长」与设计稿一致
        baseline = max(0, int(hours * 3600) - used)
        games.append({
            "id": gid, "name": name, "exe": exe, "process": proc,
            "cover": "", "baseline_seconds": baseline,
            "created_at": (_NOW - timedelta(days=240)).isoformat(timespec="seconds"),
            "sessions": sess,
        })
    return {"version": 1, "settings": dict(DEFAULT_SETTINGS), "games": games, "seeded": True}


# ------------------------------------------------------------------ 读写
def _clean_stale_tmp():
    """清理上次崩溃残留的临时写文件（唯一 tmp 名，正常流程不会残留）"""
    try:
        for p in Path(DATA_DIR).glob(os.path.basename(DATA_FILE) + ".tmp.*"):
            try:
                p.unlink()
            except OSError:
                pass
    except Exception:
        pass


def load() -> dict:
    global LOAD_WARNING
    LOAD_WARNING = None
    if not os.path.isfile(DATA_FILE):
        db = _seed_db()
        save(db)
        return db
    try:
        # utf-8-sig：兼容记事本 / PowerShell 5.1 写出的带 BOM 文件。
        # 之前用 utf-8 会把「有 BOM 但内容完全合法」的 data.json 误判为损坏。
        with open(DATA_FILE, "r", encoding="utf-8-sig") as f:
            db = json.load(f)
        if not isinstance(db, dict):
            raise ValueError("data.json 顶层不是对象")
    except Exception:
        # 数据文件确实损坏：备份原文件，从空库重新开始。
        # 绝不再用演示种子数据冒充真实记录（那会让用户误以为游戏时长还在。
        bak = DATA_FILE + ".corrupt-" + datetime.now().strftime("%Y%m%d-%H%M%S")
        try:
            shutil.copyfile(DATA_FILE, bak)
            LOAD_WARNING = bak
        except Exception:
            LOAD_WARNING = "(备份失败，原文件仍在原路径)"
        db = {"version": 1, "settings": dict(DEFAULT_SETTINGS), "games": []}
    _clean_stale_tmp()
    db.setdefault("settings", dict(DEFAULT_SETTINGS))
    for k, v in DEFAULT_SETTINGS.items():
        db["settings"].setdefault(k, v)
    db.setdefault("games", [])
    for g in db["games"]:
        # 旧版本/外部写入的多余字段（如 category）按设计原样保留，
        # 缺失的核心字段在此补默认值，保证向后兼容
        g.setdefault("sessions", [])
        g.setdefault("baseline_seconds", 0)
    return db


_save_lock = threading.Lock()


def save(db: dict):
    # 唯一 tmp 名：避免监控线程与界面线程（或多个实例）并发写同一临时文件
    with _save_lock:
        os.makedirs(DATA_DIR, exist_ok=True)
        tmp = f"{DATA_FILE}.tmp.{os.getpid()}.{threading.get_ident()}"
        try:
            # json.dumps 持有 GIL，与其他线程的修改互斥；先在内存里序列化完毕再落盘
            data = json.dumps(db, ensure_ascii=False, indent=2)
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(data)
            os.replace(tmp, DATA_FILE)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise


# ------------------------------------------------------------------ 游戏操作
def new_game(name: str, exe: str, process: str) -> dict:
    return {
        "id": uuid.uuid4().hex[:10], "name": name, "exe": exe, "process": process,
        "cover": "", "baseline_seconds": 0,
        "created_at": datetime.now().isoformat(timespec="seconds"), "sessions": [],
    }


def upsert_session(db: dict, game_id: str, session: dict):
    """按会话 id 更新或追加（用于进行中会话的周期落盘，保证崩溃后可恢复）"""
    for g in list(db["games"]):
        if g["id"] == game_id:
            for i, s in enumerate(list(g["sessions"])):
                if s.get("id") == session.get("id"):
                    g["sessions"][i] = session
                    return
            g["sessions"].append(session)
            return


def remove_session(db: dict, game_id: str, session_id: str):
    """删除一条会话记录（时长不足 5 秒被丢弃时用）"""
    for g in list(db["games"]):
        if g["id"] == game_id:
            g["sessions"] = [s for s in g["sessions"] if s.get("id") != session_id]
            return


# ------------------------------------------------------------------ 统计
def _parse(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return datetime.now()


def _span(s: dict) -> tuple[datetime, datetime]:
    """一条会话的 [开始, 结束) 时间轴（秒数异常时按 0 处理）"""
    st = _parse(s["start"])
    try:
        sec = max(0, int(s.get("seconds", 0)))
    except (TypeError, ValueError):
        sec = 0
    return st, st + timedelta(seconds=sec)


def _overlap(a0: datetime, a1: datetime, b0: datetime, b1: datetime) -> float:
    """两段区间的重叠秒数"""
    lo, hi = max(a0, b0), min(a1, b1)
    return max(0.0, (hi - lo).total_seconds())


def total_seconds(g: dict) -> int:
    """历史基线 + 全部会话 = 总时长"""
    return int(g.get("baseline_seconds", 0)) + sum(
        int(s.get("seconds", 0)) for s in list(g.get("sessions", [])))


def range_seconds(g: dict, start: datetime, end: datetime) -> int:
    """会话与 [start, end) 的重叠秒数。

    跨天/跨周边界的会话按实际重合时间拆分归属，
    例如昨晚 23:50 玩到今早 00:10，50 分钟算昨晚、20 分钟算今早。
    """
    tot = 0.0
    for s in list(g.get("sessions", [])):
        s0, s1 = _span(s)
        tot += _overlap(s0, s1, start, end)
    return int(tot)


def last_played(g: dict) -> datetime | None:
    sessions = list(g.get("sessions", []))
    if not sessions:
        return None
    return max(_parse(s["end"]) for s in sessions)


def week_start(d: date = None) -> datetime:
    d = d or date.today()
    return datetime.combine(d - timedelta(days=d.weekday()), datetime.min.time())


def month_start(d: date = None) -> datetime:
    d = d or date.today()
    return datetime.combine(d.replace(day=1), datetime.min.time())


def library_rows(db: dict) -> list[dict]:
    """游戏库表格行数据"""
    ws = week_start()
    now = datetime.now()
    out = []
    for g in list(db["games"]):
        out.append({
            "id": g["id"], "name": g["name"],
            "total": total_seconds(g), "week": range_seconds(g, ws, now),
            "last": last_played(g), "running": False,
        })
    out.sort(key=lambda r: (-r["total"], -r["week"]))
    return out


def daily_series(db: dict, days: int = 30) -> list[tuple[str, float]]:
    today = date.today()
    out = []
    for i in range(days - 1, -1, -1):
        d = today - timedelta(days=i)
        s = datetime.combine(d, datetime.min.time())
        e = s + timedelta(days=1)
        h = sum(range_seconds(g, s, e) for g in db["games"]) / 3600.0
        out.append((f"{d.month:02d}-{d.day:02d}", round(h, 2)))
    return out


def weekday_series(db: dict) -> list[tuple[str, float]]:
    ws = week_start()
    labels = ["一", "二", "三", "四", "五", "六", "日"]
    out = []
    for i in range(7):
        s = ws + timedelta(days=i)
        e = s + timedelta(days=1)
        h = sum(range_seconds(g, s, e) for g in db["games"]) / 3600.0
        out.append((labels[i], round(h, 2)))
    return out


def distribution(db: dict, top: int = 4) -> list[tuple[str, float, str]]:
    """返回 [(名称, 小时, 颜色)]，其余归入「其他」"""
    palette = ["#2EA7FF", "#FF4D6D", "#FFB454", "#13DDC4", "#9381FF"]
    rows = sorted(db["games"], key=lambda g: -total_seconds(g))
    out = []
    for i, g in enumerate(rows[:top]):
        out.append((g["name"], round(total_seconds(g) / 3600.0, 1), palette[i % len(palette)]))
    rest = sum(total_seconds(g) for g in rows[top:]) / 3600.0
    if rest > 0.05:
        out.append(("其他", round(rest, 1), "#9381FF"))
    return out


def longest_session(db: dict) -> float:
    best = 0
    for g in db["games"]:
        for s in list(g["sessions"]):
            best = max(best, int(s.get("seconds", 0)))
    return best / 3600.0


def session_count(db: dict, start: datetime = None) -> int:
    """会话条数；给定 start 时只数与 [start, now) 有重叠的会话"""
    now = datetime.now()
    n = 0
    for g in db["games"]:
        for s in list(g["sessions"]):
            if start is None:
                n += 1
                continue
            s0, s1 = _span(s)
            if _overlap(s0, s1, start, now) > 0:
                n += 1
    return n


def active_days(db: dict, since: datetime) -> int:
    """since 以来出现过会话的自然日数量（跨天会话在两天都计入）"""
    today = date.today()
    days = set()
    for g in db["games"]:
        for s in list(g["sessions"]):
            s0, s1 = _span(s)
            d = max(s0.date(), since.date())
            end_d = min(s1.date(), today)
            while d <= end_d:
                d0 = datetime.combine(d, datetime.min.time())
                if _overlap(s0, s1, d0, d0 + timedelta(days=1)) > 0:
                    days.add(d)
                d += timedelta(days=1)
    return len(days)


def export_csv(db: dict, path: str) -> int:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    rows = 0
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["游戏", "开始时间", "结束时间", "时长(分钟)"])
        for g in list(db["games"]):
            for s in list(g.get("sessions", [])):
                w.writerow([g["name"], s["start"], s["end"],
                            round(int(s.get("seconds", 0)) / 60.0, 1)])
                rows += 1
    return rows
