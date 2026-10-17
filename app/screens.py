# -*- coding: utf-8 -*-
"""三个界面：01 游戏库 / 02 统计分析 / 03 设置"""
from __future__ import annotations

import os
import shutil
from datetime import datetime

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
                               QVBoxLayout, QWidget)

from app import storage, theme
from app.charts import BarChart, DonutChart, ProgressBar, StatusDot
from app.icons import Icon
from app.widgets import (Card, StatCard, ToggleRow, card_header, h_divider)


def fmt_h(hours: float) -> str:
    return f"{hours:,.1f}"


# ------------------------------------------------------------------ 通用件
class SearchBox(QFrame):
    def __init__(self, placeholder="搜索游戏…", width=260, parent=None):
        super().__init__(parent)
        self.setFixedSize(width, 34)
        self.setStyleSheet(f"""
            QFrame {{ background-color: {theme.FIELD_BG}; border: 1px solid {theme.FIELD_LINE};
                      border-radius: {theme.R_PILL}px; }}
            QLineEdit {{ background: transparent; border: none; color: {theme.TXT_1};
                        font-size: 12px; padding: 0; }}""")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(11, 0, 12, 0)
        lay.setSpacing(7)
        lay.addWidget(Icon("search", 14, theme.TXT_3))
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setFont(theme.ui(12))
        lay.addWidget(self.edit)


class Segmented(QFrame):
    changed = Signal(str)

    def __init__(self, items, active=None, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.setStyleSheet(f"""
            QFrame {{ background-color: rgba(20,24,32,0.04);
                      border: 1px solid {theme.CARD_LINE}; border-radius: {theme.R_SM}px; }}""")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        self.buttons = {}
        active = active or items[0]
        for label in items:
            b = QPushButton(label)
            b.setObjectName("seg")
            b.setProperty("on", "true" if label == active else "false")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyle(b.style())
            b.clicked.connect(lambda _=False, l=label: self._pick(l))
            self.buttons[label] = b
            lay.addWidget(b)
        self.active = active

    def _pick(self, label):
        for l, b in self.buttons.items():
            b.setProperty("on", "true" if l == label else "false")
            b.setStyle(b.style())
        self.active = label
        self.changed.emit(label)


class TopBar(QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(theme.TOPBAR_H)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(12)
        t = QLabel(title)
        t.setObjectName("page_title")
        lay.addWidget(t)
        self.right = QHBoxLayout()
        self.right.setSpacing(10)
        lay.addStretch(1)
        lay.addLayout(self.right)

    def add_right(self, w):
        self.right.addWidget(w, 0, Qt.AlignmentFlag.AlignVCenter)


class BaseScreen(QWidget):
    TITLE = ""

    def __init__(self, ctx, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.top = TopBar(self.TITLE)
        lay.addWidget(self.top)
        lay.addWidget(h_divider())
        self.content = QWidget()
        self.content_lay = QVBoxLayout(self.content)
        self.content_lay.setContentsMargins(theme.PAD_CONTENT, theme.PAD_CONTENT,
                                            theme.PAD_CONTENT, theme.PAD_CONTENT)
        self.content_lay.setSpacing(theme.GAP)
        lay.addWidget(self.content, 1)


# ------------------------------------------------------------------ 01 游戏库
class GameRow(QWidget):
    W_TOTAL, W_WEEK, W_LAST, W_STATE = 100, 80, 120, 92

    def __init__(self, row: dict, parent=None):
        super().__init__(parent)
        self.row = row
        self._hover = False
        self.setFixedHeight(54)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.status_dot = None
        self.state_label = None
        self._build()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 16, 0)
        lay.setSpacing(12)

        # 游戏
        self.mark = CoverMark(self.row["name"], 32)
        lay.addWidget(self.mark, 0, Qt.AlignmentFlag.AlignVCenter)
        n = QLabel(self.row["name"])
        n.setStyleSheet("color:rgba(20,24,32,0.92);font-size:13px;font-weight:600;")
        lay.addWidget(n, 1)

        for text, w, mono, color in (
            (f"{fmt_h(self.row['total'] / 3600)}h", self.W_TOTAL, True, "rgba(20,24,32,0.92)"),
            (f"{fmt_h(self.row['week'] / 3600)}h", self.W_WEEK, True, "rgba(20,24,32,0.72)"),
            (self._last_text(), self.W_LAST, False, "rgba(20,24,32,0.5)"),
        ):
            lb = QLabel(text)
            lb.setFixedWidth(w)
            lb.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lb.setFont(theme.mono(12.5) if mono else theme.ui(11.5))
            lb.setStyleSheet(f"color:{color};")
            lay.addWidget(lb, 0, Qt.AlignmentFlag.AlignVCenter)

        st = QWidget()
        st.setFixedWidth(self.W_STATE)
        sl = QHBoxLayout(st)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(6)
        sl.addStretch(1)
        self.status_dot = StatusDot(theme.CYAN, 6, glow=False)
        self.state_label = QLabel("运行中")
        self.state_label.setFont(theme.ui(11.5))
        sl.addWidget(self.status_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        sl.addWidget(self.state_label, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(st, 0, Qt.AlignmentFlag.AlignVCenter)
        self.set_running(self.row.get("running", False))

    def _last_text(self) -> str:
        lp = self.row.get("last")
        if not lp:
            return "—"
        d = lp.date()
        today = datetime.now().date()
        if d == today:
            return f"今天 {lp.strftime('%H:%M')}"
        if (today - d).days == 1:
            return f"昨天 {lp.strftime('%H:%M')}"
        return lp.strftime("%m-%d %H:%M")

    def set_running(self, on: bool):
        self.status_dot.color = theme.CYAN if on else "rgba(20,24,32,0.22)"
        self.state_label.setText("运行中" if on else "未运行")
        self.state_label.setStyleSheet(
            f"color:{theme.CYAN if on else 'rgba(20,24,32,0.35)'};")
        self.status_dot.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._hover:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(20, 24, 32, 12))
            p.drawRoundedRect(QRectF(6, 2, self.width() - 12, self.height() - 4), 10, 10)
        p.setPen(QColor(20, 24, 32, 14))
        p.drawLine(QPointF(16, self.height() - 0.5), QPointF(self.width() - 16, self.height() - 0.5))
        p.end()


class CoverMark(QWidget):
    """封面色块：用名称哈希出渐变色"""

    _PALETTE = [(theme.CYAN, theme.BLUE), (theme.PURPLE, theme.RED), (theme.BLUE, theme.PURPLE),
                (theme.ORANGE, theme.RED), (theme.CYAN, theme.PURPLE)]

    def __init__(self, name: str, size=32, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        pair = self._PALETTE[sum(ord(c) for c in name) % len(self._PALETTE)]
        self.c1, self.c2 = pair
        self.initial = (name.strip()[:1] or "?")

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        g = QLinearGradient(QPointF(0, 0), QPointF(self.width(), self.height()))
        c1 = QColor(self.c1); c1.setAlphaF(0.85)
        c2 = QColor(self.c2); c2.setAlphaF(0.55)
        g.setColorAt(0.0, c1)
        g.setColorAt(1.0, c2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(g)
        p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 8, 8)
        p.setPen(QColor(255, 255, 255, 210))
        p.setFont(theme.ui(self.height() * 0.42, theme.SemiBold))
        p.drawText(QRectF(0, 0, self.width(), self.height()), Qt.AlignmentFlag.AlignCenter,
                   self.initial)
        p.end()


class GameTable(Card):
    HEADERS = [("游戏", 0), ("总时长", GameRow.W_TOTAL), ("本周", GameRow.W_WEEK),
               ("最近游玩", GameRow.W_LAST), ("状态", GameRow.W_STATE)]

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        head = QWidget()
        head.setFixedHeight(42)
        hl = QHBoxLayout(head)
        hl.setContentsMargins(16, 0, 16, 0)
        hl.setSpacing(12)
        first = True
        for text, w in self.HEADERS:
            lb = QLabel(text)
            lb.setObjectName("card_sub")
            lb.setFont(theme.ui(11.5, theme.SemiBold))
            lb.setStyleSheet("color:rgba(20,24,32,0.40);")
            if w:
                lb.setFixedWidth(w)
                lb.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if first:
                hl.addSpacing(44)
                first = False
            hl.addWidget(lb, 0 if w else 1)
        lay.addWidget(head)
        lay.addWidget(h_divider())

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.body = QWidget()
        self.body_lay = QVBoxLayout(self.body)
        self.body_lay.setContentsMargins(0, 0, 0, 0)
        self.body_lay.setSpacing(0)
        self.body_lay.addStretch(1)
        self.scroll.setWidget(self.body)
        self.scroll.setStyleSheet("QScrollArea{background:transparent;border:none;}")
        lay.addWidget(self.scroll, 1)

        self.rows: dict[str, GameRow] = {}

    def set_rows(self, rows: list[dict]):
        while self.body_lay.count():
            item = self.body_lay.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        self.rows.clear()
        for r in rows:
            gr = GameRow(r)
            self.body_lay.addWidget(gr)
            self.rows[r["id"]] = gr
        self.body_lay.addStretch(1)

    def set_running(self, ids: set[str]):
        for gid, gr in self.rows.items():
            gr.set_running(gid in ids)


class LibraryScreen(BaseScreen):
    TITLE = "游戏库"

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self._build_top()

        # KPI 行
        kpi = QHBoxLayout()
        kpi.setSpacing(theme.GAP)
        self.k_total = StatCard("总游戏时长", "0.0", "小时", "chart", theme.CYAN)
        self.k_week = StatCard("本周时长", "0.0", "小时", "chart", theme.BLUE)
        self.k_long = StatCard("最长单次", "0.0", "小时", "chart", theme.PURPLE)
        self.k_days = StatCard("本月活跃", "0", "天", "grid", theme.ORANGE)
        for c in (self.k_total, self.k_week, self.k_long, self.k_days):
            kpi.addWidget(c)
        self.content_lay.addLayout(kpi)

        # 主行
        main = QHBoxLayout()
        main.setSpacing(theme.GAP)

        self.table = GameTable()
        main.addWidget(self.table, 1)

        right = QVBoxLayout()
        right.setSpacing(theme.GAP)

        # 正在游玩
        self.now_card = Card()
        nc = QVBoxLayout(self.now_card)
        nc.setContentsMargins(16, 14, 16, 16)
        nc.setSpacing(12)
        nc.addWidget(card_header("正在游玩", "", StatusDot(theme.CYAN, 7)))
        self.now_name = QLabel("暂无游戏运行")
        self.now_name.setStyleSheet(f"color:{theme.TXT_1};font-size:13.5px;font-weight:600;")
        nc.addWidget(self.now_name)
        self.now_timer = QLabel("00:00:00")
        self.now_timer.setFont(theme.mono(30, theme.SemiBold))
        self.now_timer.setStyleSheet(f"color:{theme.TXT_1};")
        nc.addWidget(self.now_timer)
        goal_row = QHBoxLayout()
        self.goal_label = QLabel("本周目标 40 小时")
        self.goal_label.setObjectName("card_sub")
        self.goal_pct = QLabel("0%")
        self.goal_pct.setFont(theme.mono(12, theme.SemiBold))
        self.goal_pct.setStyleSheet(f"color:{theme.CYAN};")
        goal_row.addWidget(self.goal_label)
        goal_row.addStretch(1)
        goal_row.addWidget(self.goal_pct)
        nc.addLayout(goal_row)
        self.goal_bar = ProgressBar(0.0, theme.CYAN, 6)
        nc.addWidget(self.goal_bar)
        btns = QHBoxLayout()
        btns.setSpacing(10)
        self.btn_pause = QPushButton("暂停记录")
        self.btn_pause.setObjectName("ghost")
        self.btn_end = QPushButton("结束")
        self.btn_end.setObjectName("ghost")
        for b in (self.btn_pause, self.btn_end):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            btns.addWidget(b)
        nc.addLayout(btns)
        right.addWidget(self.now_card)

        # 本周分布
        self.week_card = Card()
        wc = QVBoxLayout(self.week_card)
        wc.setContentsMargins(16, 14, 16, 16)
        wc.setSpacing(12)
        wc.addWidget(card_header("本周时长分布", "单位：小时"))
        self.week_chart = BarChart([], theme.CYAN, -1, True)
        self.week_chart.setFixedHeight(120)
        wc.addWidget(self.week_chart)
        right.addWidget(self.week_card)
        right.addStretch(1)

        right_wrap = QWidget()
        right_wrap.setFixedWidth(theme.RIGHT_W)
        right_wrap.setLayout(right)
        main.addWidget(right_wrap, 0)
        self.content_lay.addLayout(main, 1)

        self.btn_pause.clicked.connect(self._toggle_pause)
        self.btn_end.clicked.connect(self._end_session)

    def _build_top(self):
        self.search = SearchBox("搜索游戏…", 260)
        self.search.edit.textChanged.connect(self.refresh)
        self.top.add_right(self.search)
        btn = QPushButton("添加游戏")
        btn.setObjectName("primary")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda: self.ctx.goto("settings"))
        self.top.add_right(btn)

    def _toggle_pause(self):
        gid = self._active_id()
        if not gid:
            return
        if self.ctx.monitor.is_paused(gid):
            self.ctx.monitor.resume(gid)
            self.btn_pause.setText("暂停记录")
        else:
            self.ctx.monitor.pause(gid)
            self.btn_pause.setText("继续记录")

    def _end_session(self):
        gid = self._active_id()
        if not gid:
            return
        sec = self.ctx.monitor.elapsed(gid)
        if sec >= 5:
            storage.add_session(self.ctx.db, gid, sec)
            self.ctx.save()
        self.ctx.monitor._active.pop(gid, None)
        self.btn_pause.setText("暂停记录")
        self.ctx.refresh_all()

    def _active_id(self):
        ids = self.ctx.monitor.active_ids()
        return next(iter(ids), None)

    def refresh(self):
        db = self.ctx.db
        rows = storage.library_rows(db)
        q = self.search.edit.text().strip().lower()
        if q:
            rows = [r for r in rows if q in r["name"].lower()]
        running = self.ctx.monitor.active_ids()
        for r in rows:
            r["running"] = r["id"] in running
        self.table.set_rows(rows)
        self.table.set_running(running)

        # KPI
        total = sum(storage.total_seconds(g) for g in db["games"]) / 3600.0
        ws = storage.week_start()
        week = sum(storage.range_seconds(g, ws, datetime.now())
                   for g in db["games"]) / 3600.0
        days = storage.active_days(db, storage.month_start())
        self.k_total.set_value(fmt_h(total))
        self.k_week.set_value(fmt_h(week))
        self.k_long.set_value(fmt_h(storage.longest_session(db)))
        self.k_days.set_value(str(days))

        # 正在游玩
        gid = self._active_id()
        if gid:
            g = next((x for x in db["games"] if x["id"] == gid), None)
            self.now_name.setText(g["name"] if g else "")
            self.now_timer.setText(theme.fmt_hms(self.ctx.monitor.elapsed(gid)))
            self.btn_pause.setEnabled(True)
            self.btn_end.setEnabled(True)
            self.btn_pause.setText("继续记录" if self.ctx.monitor.is_paused(gid) else "暂停记录")
        else:
            self.now_name.setText("暂无游戏运行")
            self.now_timer.setText("00:00:00")
            self.btn_pause.setEnabled(False)
            self.btn_end.setEnabled(False)

        goal = float(db["settings"].get("week_goal_hours", 40)) or 40
        self.goal_label.setText(f"本周目标 {goal:g} 小时")
        pct = min(week / goal, 1.0)
        self.goal_bar.set_value(pct)
        self.goal_pct.setText(f"{pct * 100:.0f}%")

        # 周分布
        self.week_chart.set_data(storage.weekday_series(db),
                                 datetime.now().weekday())

    def on_tick(self):
        gid = self._active_id()
        if gid:
            self.now_timer.setText(theme.fmt_hms(self.ctx.monitor.elapsed(gid)))


# ------------------------------------------------------------------ 02 统计分析
class LegendRow(QWidget):
    def __init__(self, name, pct, hours, color, parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)

        dot = QWidget()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background:{color};border-radius:4px;")
        lay.addWidget(dot, 0, Qt.AlignmentFlag.AlignVCenter)

        n = QLabel(name)
        n.setStyleSheet("color:rgba(20,24,32,0.82);font-size:11.5px;")
        lay.addWidget(n, 1)

        p = QLabel(f"{pct:.0f}%")
        p.setFont(theme.mono(11))
        p.setStyleSheet("color:rgba(20,24,32,0.55);")
        lay.addWidget(p, 0)

        h = QLabel(f"{fmt_h(hours)}h")
        h.setFont(theme.mono(11))
        h.setStyleSheet("color:rgba(20,24,32,0.55);")
        h.setFixedWidth(56)
        h.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.addWidget(h, 0)


class AnalyticsScreen(BaseScreen):
    TITLE = "统计分析"

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self.range_key = "本周"
        self._build_top()

        kpi = QHBoxLayout()
        kpi.setSpacing(theme.GAP)
        self.k_hours = StatCard("本周时长", "0.0", "小时", "chart", theme.BLUE)
        self.k_sessions = StatCard("总会话数", "0", "次", "grid", theme.CYAN)
        self.k_avg = StatCard("平均单次", "0.0", "小时", "chart", theme.PURPLE)
        for c in (self.k_hours, self.k_sessions, self.k_avg):
            kpi.addWidget(c)
        self.content_lay.addLayout(kpi)

        main = QHBoxLayout()
        main.setSpacing(theme.GAP)

        # 每日趋势
        trend = Card()
        tl = QVBoxLayout(trend)
        tl.setContentsMargins(16, 14, 16, 16)
        tl.setSpacing(12)
        self.trend_sub = QLabel("最近 30 天")
        tl.addWidget(card_header("每日时长趋势", "", self.trend_sub))
        self.trend_chart = BarChart([], theme.CYAN, -1, True)
        self.trend_chart.setMinimumHeight(200)
        tl.addWidget(self.trend_chart, 1)
        main.addWidget(trend, 1)

        # 分布
        dist = Card()
        dist.setFixedWidth(theme.RIGHT_W)
        dl = QVBoxLayout(dist)
        dl.setContentsMargins(16, 14, 16, 16)
        dl.setSpacing(14)
        dl.addWidget(card_header("时长占比", "按游戏"))
        self.donut = DonutChart([], "0.0", "小时", 18)
        self.donut.setFixedSize(160, 160)
        dl.addWidget(self.donut, 0, Qt.AlignmentFlag.AlignHCenter)
        self.legend_box = QWidget()
        self.legend_lay = QVBoxLayout(self.legend_box)
        self.legend_lay.setContentsMargins(0, 0, 0, 0)
        self.legend_lay.setSpacing(6)
        dl.addWidget(self.legend_box)
        dl.addStretch(1)
        main.addWidget(dist, 0)

        self.content_lay.addLayout(main, 1)

    def _build_top(self):
        self.seg = Segmented(["本周", "本月", "全部"])
        self.seg.changed.connect(self._on_range)
        self.top.add_right(self.seg)
        b = QPushButton("导出 CSV")
        b.setObjectName("ghost")
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(self._export)
        self.top.add_right(b)

    def _on_range(self, key):
        self.range_key = key
        self.k_hours.set_label({"本周": "本周时长", "本月": "本月时长", "全部": "累计时长"}[key])
        self.refresh()

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出 CSV", "playtime_sessions.csv",
                                              "CSV 文件 (*.csv)")
        if not path:
            return
        n = storage.export_csv(self.ctx.db, path)
        QMessageBox.information(self, "已导出", f"共 {n} 条会话记录\n{path}")

    def _range(self):
        now = datetime.now()
        if self.range_key == "本周":
            return storage.week_start(), now, "最近 7 天"
        if self.range_key == "本月":
            return storage.month_start(), now, "本月至今"
        return datetime(1970, 1, 1), now, "全部时间"

    def refresh(self):
        db = self.ctx.db
        start, end, sub = self._range()
        self.trend_sub.setText("最近 30 天")

        hours = sum(storage.range_seconds(g, start, end) for g in db["games"]) / 3600.0
        # 「会话数」展示累计总会话数；「平均单次」跟随当前所选范围
        cnt_total = storage.session_count(db)
        cnt_range = storage.session_count(db, start if self.range_key != "全部" else None)
        avg = hours / cnt_range if cnt_range else 0.0
        self.k_hours.set_value(fmt_h(hours))
        self.k_sessions.set_value(str(cnt_total))
        self.k_avg.set_value(fmt_h(avg))

        # 趋势图固定展示最近 30 天（对齐设计稿）
        self.trend_chart.set_data(storage.daily_series(db, 30), 29)

        dist = storage.distribution(db, 4)
        total = sum(v for _, v, _ in dist) or 1.0
        self.donut.set_segments([(v, c, n) for n, v, c in dist], fmt_h(total), "小时")

        while self.legend_lay.count():
            it = self.legend_lay.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None)
        for n, v, c in dist:
            self.legend_lay.addWidget(LegendRow(n, v / total * 100, v, c))


# ------------------------------------------------------------------ 03 设置
class Field(QWidget):
    def __init__(self, label: str, placeholder="", value="", parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        t = QLabel(label)
        t.setStyleSheet("color:rgba(20,24,32,0.62);font-size:11.5px;font-weight:500;")
        lay.addWidget(t)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(placeholder)
        self.edit.setText(value)
        self.edit.setFont(theme.ui(12))
        self.edit.setFixedHeight(34)
        lay.addWidget(self.edit)


class SettingsScreen(BaseScreen):
    TITLE = "设置"

    def __init__(self, ctx, parent=None):
        super().__init__(ctx, parent)
        self._build_top()

        body = QHBoxLayout()
        body.setSpacing(theme.GAP)

        # 添加游戏
        form = Card()
        fl = QVBoxLayout(form)
        fl.setContentsMargins(18, 16, 18, 18)
        fl.setSpacing(14)
        fl.addWidget(card_header("添加游戏", "登记可执行文件后即可自动统计"))

        self.f_name = Field("游戏名称", "输入游戏显示名称")
        fl.addWidget(self.f_name)

        exe_row = QHBoxLayout()
        exe_row.setSpacing(10)
        self.f_exe = Field("可执行文件", "例如 D:\\Games\\Cyberpunk 2077\\bin\\x64\\Cyberpunk2077.exe")
        self.f_exe.edit.textChanged.connect(self._sync_process)
        exe_row.addWidget(self.f_exe, 1)
        browse = QPushButton("浏览")
        browse.setObjectName("ghost")
        browse.setFixedHeight(34)
        browse.setCursor(Qt.CursorShape.PointingHandCursor)
        browse.clicked.connect(self._browse)
        exe_row.addWidget(browse, 0, Qt.AlignmentFlag.AlignBottom)
        fl.addLayout(exe_row)

        self.f_proc = Field("进程名称", "例如 Cyberpunk2077.exe")
        fl.addWidget(self.f_proc)

        fl.addStretch(1)

        btns = QHBoxLayout()
        btns.setSpacing(10)
        save = QPushButton("保存")
        save.setObjectName("primary")
        cancel = QPushButton("取消")
        cancel.setObjectName("ghost")
        for b in (save, cancel):
            b.setFixedHeight(34)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            btns.addWidget(b)
        btns.addStretch(1)
        fl.addLayout(btns)
        save.clicked.connect(self._save_game)
        cancel.clicked.connect(self._clear_form)

        body.addWidget(form, 1)

        # 右列
        right = QWidget()
        right.setFixedWidth(theme.RIGHT_W)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(theme.GAP)

        mon = Card()
        ml = QVBoxLayout(mon)
        ml.setContentsMargins(16, 14, 16, 16)
        ml.setSpacing(10)
        ml.addWidget(card_header("监控设置", "控制后台追踪行为"))
        self.sw_autostart = ToggleRow("开机自启动", "登录 Windows 后自动运行", False)
        self.sw_tray = ToggleRow("最小化到托盘", "关闭窗口时保留后台监控", True)
        self.sw_idle = ToggleRow("空闲自动暂停", "鼠标键盘无操作 5 分钟后暂停计时", True)
        rows_sw = [self.sw_autostart, self.sw_tray, self.sw_idle]
        for i, row in enumerate(rows_sw):
            ml.addWidget(row)
            if i < len(rows_sw) - 1:
                ml.addWidget(h_divider())
        ml.addStretch(1)
        rl.addWidget(mon)

        data = Card()
        dnl = QVBoxLayout(data)
        dnl.setContentsMargins(16, 14, 16, 16)
        dnl.setSpacing(12)
        dnl.addWidget(card_header("数据管理", "全部数据保存在本机"))
        b1 = QPushButton("导出 CSV")
        b2 = QPushButton("备份到本地")
        b3 = QPushButton("清空数据")
        b1.setObjectName("ghost")
        b2.setObjectName("ghost")
        b3.setObjectName("danger")
        for b in (b1, b2, b3):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            dnl.addWidget(b)
        b1.clicked.connect(self._export)
        b2.clicked.connect(self._backup)
        b3.clicked.connect(self._wipe)
        rl.addWidget(data)
        rl.addStretch(1)

        body.addWidget(right, 0)
        self.content_lay.addLayout(body, 1)

    def _build_top(self):
        b = QPushButton("保存更改")
        b.setObjectName("primary")
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.clicked.connect(self._save_settings)
        self.top.add_right(b)

    def _sync_process(self, text):
        if not self.f_proc.edit.text().strip():
            self.f_proc.edit.setText(os.path.basename(text.strip()))

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择游戏可执行文件", "",
                                              "可执行文件 (*.exe);;所有文件 (*.*)")
        if path:
            self.f_exe.edit.setText(path)
            self.f_proc.edit.setText(os.path.basename(path))
            if not self.f_name.edit.text().strip():
                self.f_name.edit.setText(os.path.splitext(os.path.basename(path))[0])

    def _clear_form(self):
        for f in (self.f_name, self.f_exe, self.f_proc):
            f.edit.clear()

    def _save_game(self):
        name = self.f_name.edit.text().strip()
        if not name:
            QMessageBox.warning(self, "缺少信息", "请填写游戏名称")
            return
        g = storage.new_game(name, self.f_exe.edit.text().strip(),
                             self.f_proc.edit.text().strip() or os.path.basename(
                                 self.f_exe.edit.text().strip()))
        self.ctx.db["games"].append(g)
        self.ctx.save()
        self._clear_form()
        self.ctx.refresh_all()
        QMessageBox.information(self, "已添加", f"「{name}」已加入监控列表")

    def _save_settings(self):
        s = self.ctx.db["settings"]
        s["autostart"] = self.sw_autostart.sw.is_checked()
        s["minimize_to_tray"] = self.sw_tray.sw.is_checked()
        s["idle_pause"] = self.sw_idle.sw.is_checked()
        self.ctx.save()
        self.ctx.apply_settings()
        QMessageBox.information(self, "已保存", "设置已生效")

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出 CSV", "playtime_sessions.csv",
                                              "CSV 文件 (*.csv)")
        if path:
            n = storage.export_csv(self.ctx.db, path)
            QMessageBox.information(self, "已导出", f"共 {n} 条会话记录")

    def _backup(self):
        path, _ = QFileDialog.getSaveFileName(self, "备份数据", "playtime_backup.json",
                                              "JSON 文件 (*.json)")
        if path:
            shutil.copyfile(storage.DATA_FILE, path)
            QMessageBox.information(self, "已备份", path)

    def _wipe(self):
        r = QMessageBox.question(self, "清空数据", "将删除全部游戏与时长记录，且不可恢复。继续？",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self.ctx.db["games"] = []
            self.ctx.db["seeded"] = False
            self.ctx.save()
            self.ctx.refresh_all()

    def refresh(self):
        s = self.ctx.db["settings"]
        self.sw_autostart.sw.setChecked(bool(s.get("autostart")), False)
        self.sw_tray.sw.setChecked(bool(s.get("minimize_to_tray")), False)
        self.sw_idle.sw.setChecked(bool(s.get("idle_pause")), False)
