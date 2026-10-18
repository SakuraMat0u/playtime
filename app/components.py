# -*- coding: utf-8 -*-
"""界面通用组件：搜索框 / 分段切换 / 顶栏 / 界面基座 / 游戏行 / 表格 / 图例行 / 表单字段"""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from app import theme
from app.charts import StatusDot, gradient_tile
from app.icons import Icon
from app.widgets import Card, clear_layout, h_divider


def fmt_h(hours: float) -> str:
    """小时 -> 1 位小数（带千分位）"""
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
    """分段切换控件（本周 / 本月 / 全部）"""

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
            b.style().unpolish(b)
            b.style().polish(b)
        self.active = label
        self.changed.emit(label)


class TopBar(QWidget):
    """界面顶栏：标题 + 右侧操作区"""

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
    """三个界面共用的骨架：顶栏 + 分隔线 + 内容区"""

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
    """游戏库表格中的一行"""

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
        gradient_tile(p, QRectF(0, 0, self.width(), self.height()),
                      self.c1, self.c2, 8, alpha1=0.85, alpha2=0.55)
        p.setPen(QColor(255, 255, 255, 210))
        p.setFont(theme.ui(self.height() * 0.42, theme.SemiBold))
        p.drawText(QRectF(0, 0, self.width(), self.height()), Qt.AlignmentFlag.AlignCenter,
                   self.initial)
        p.end()


class GameTable(Card):
    """游戏列表：表头 + 可滚动行区"""

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
        clear_layout(self.body_lay)
        self.rows.clear()
        for r in rows:
            gr = GameRow(r)
            self.body_lay.addWidget(gr)
            self.rows[r["id"]] = gr
        self.body_lay.addStretch(1)

    def set_running(self, ids: set[str]):
        for gid, gr in self.rows.items():
            gr.set_running(gid in ids)


# ------------------------------------------------------------------ 02 统计分析
class LegendRow(QWidget):
    """环形图图例：色点 + 名称 + 百分比 + 时长"""

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


# ------------------------------------------------------------------ 03 设置
class Field(QWidget):
    """表单字段：标签 + 输入框"""

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
