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
def load() -> dict:
    if not os.path.isfile(DATA_FILE):
        db = _seed_db()
        save(db)
        return db
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
    except Exception:
        db = _seed_db()
    db.setdefault("settings", dict(DEFAULT_SETTINGS))
    for k, v in DEFAULT_SETTINGS.items():
        db["settings"].setdefault(k, v)
    db.setdefault("games", [])
    return db


def save(db: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


# ------------------------------------------------------------------ 游戏操作
def new_game(name: str, exe: str, process: str) -> dict:
    return {
        "id": uuid.uuid4().hex[:10], "name": name, "exe": exe, "process": process,
        "cover": "", "baseline_seconds": 0,
        "created_at": datetime.now().isoformat(timespec="seconds"), "sessions": [],
    }


def add_session(db: dict, game_id: str, seconds: int):
    for g in db["games"]:
        if g["id"] == game_id and seconds >= 5:
            g["sessions"].append({
                "id": uuid.uuid4().hex[:8],
                "start": (datetime.now() - timedelta(seconds=seconds)).isoformat(timespec="seconds"),
                "end": datetime.now().isoformat(timespec="seconds"),
                "seconds": int(seconds),
            })


# ------------------------------------------------------------------ 统计
def _parse(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return datetime.now()


def total_seconds(g: dict) -> int:
    """历史基线 + 全部会话 = 总时长"""
    return int(g.get("baseline_seconds", 0)) + sum(
        int(s.get("seconds", 0)) for s in g.get("sessions", []))


def range_seconds(g: dict, start: datetime, end: datetime) -> int:
    tot = 0
    for s in g.get("sessions", []):
        st = _parse(s["start"])
        if start <= st < end:
            tot += int(s.get("seconds", 0))
    return tot


def last_played(g: dict) -> datetime | None:
    if not g.get("sessions"):
        return None
    return max(_parse(s["end"]) for s in g["sessions"])


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
    for g in db["games"]:
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
        for s in g["sessions"]:
            best = max(best, int(s.get("seconds", 0)))
    return best / 3600.0


def session_count(db: dict, start: datetime = None) -> int:
    n = 0
    for g in db["games"]:
        for s in g["sessions"]:
            if start is None or _parse(s["start"]) >= start:
                n += 1
    return n


def active_days(db: dict, since: datetime) -> int:
    days = set()
    for g in db["games"]:
        for s in g["sessions"]:
            d = _parse(s["start"]).date()
            if d >= since.date():
                days.add(d)
    return len(days)


def export_csv(db: dict, path: str) -> int:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    rows = 0
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["游戏", "开始时间", "结束时间", "时长(分钟)"])
        for g in db["games"]:
            for s in g.get("sessions", []):
                w.writerow([g["name"], s["start"], s["end"],
                            round(int(s.get("seconds", 0)) / 60.0, 1)])
                rows += 1
    return rows
