# -*- coding: utf-8 -*-
"""复用控件：卡片 / KPI / 导航 / 开关 / 窗口按钮 —— 尺寸与圆角对齐设计稿"""
from PySide6.QtCore import Property, QEasingCurve, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout,
                               QWidget)

from app import theme
from app.icons import Icon, draw_icon


# ------------------------------------------------------------------ 基础块
def clear_layout(lay):
    """清空布局中的全部子控件（供列表刷新等场景复用）"""
    while lay.count():
        item = lay.takeAt(0)
        w = item.widget()
        if w is not None:
            w.setParent(None)


def h_divider() -> QFrame:
    d = QFrame()
    d.setObjectName("divider_h")
    return d


def v_divider() -> QFrame:
    d = QFrame()
    d.setObjectName("divider_v")
    return d


class Card(QFrame):
    """圆角 16 / 半透明底 / 1px 描边（样式由全局 QSS 的 QFrame#card 提供）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")


class SectionLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text.upper(), parent)
        self.setObjectName("sec_label")


# ------------------------------------------------------------------ KPI
class StatCard(Card):
    """KPI 卡片：图标 + 数值（等宽字体）+ 标题"""

    def __init__(self, label, value, unit="", icon="chart", accent=None, delta="", parent=None):
        super().__init__(parent)
        self.accent = accent or theme.CYAN
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(96)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        head = QHBoxLayout()
        head.setSpacing(6)
        ic = Icon(icon, 14, self.accent)
        head.addWidget(ic, 0, Qt.AlignmentFlag.AlignVCenter)
        self.lb = QLabel(label)
        self.lb.setObjectName("kpi_label")
        head.addWidget(self.lb, 0, Qt.AlignmentFlag.AlignVCenter)
        head.addStretch(1)
        if delta:
            dl = QLabel(delta)
            dl.setStyleSheet(f"color:{theme.CYAN};font-size:11px;font-weight:600;")
            head.addWidget(dl, 0, Qt.AlignmentFlag.AlignVCenter)
        lay.addLayout(head)

        row = QHBoxLayout()
        row.setSpacing(4)
        row.setAlignment(Qt.AlignmentFlag.AlignBottom)
        self.val = QLabel(value)
        self.val.setFont(theme.mono(26, theme.SemiBold))
        self.val.setStyleSheet(f"color:{theme.TXT_1};")
        row.addWidget(self.val, 0, Qt.AlignmentFlag.AlignBaseline)
        if unit:
            u = QLabel(unit)
            u.setObjectName("kpi_unit")
            row.addWidget(u, 0, Qt.AlignmentFlag.AlignBaseline)
        row.addStretch(1)
        lay.addLayout(row)

    def set_value(self, v: str):
        self.val.setText(v)

    def set_label(self, s: str):
        self.lb.setText(s)


# ------------------------------------------------------------------ 导航
class NavItem(QWidget):
    """侧边栏导航项：高 36 / 圆角 10"""

    clicked = Signal(str)

    def __init__(self, key, text, icon="grid", parent=None):
        super().__init__(parent)
        self.key, self.text, self.icon_name = key, text, icon
        self.active = False
        self._hover = False
        self.setFixedHeight(36)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_active(self, on: bool):
        self.active = on
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(0, 0, self.width(), self.height())
        if self.active:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(46, 167, 255, 26))
            p.drawRoundedRect(r, theme.R_NAV, theme.R_NAV)
            # 左侧强调条
            p.setBrush(QColor(theme.BLUE))
            p.drawRoundedRect(QRectF(0, 9, 2.5, self.height() - 18), 1.25, 1.25)
        elif self._hover:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(20, 24, 32, 9))
            p.drawRoundedRect(r, theme.R_NAV, theme.R_NAV)

        color = theme.BLUE if self.active else theme.TXT_2
        draw_icon(p, self.icon_name, QRectF(14, (self.height() - 16) / 2, 16, 16), color)
        p.setPen(theme.qcolor(color))
        p.setFont(theme.ui(12.5, theme.SemiBold if self.active else theme.Medium))
        p.drawText(QRectF(38, 0, self.width() - 48, self.height()),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text)
        p.end()


# ------------------------------------------------------------------ 开关
class Switch(QWidget):
    toggled = Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._t = 1.0 if checked else 0.0
        self._target = self._t      # 逻辑状态：动画进行中的点击以目标值为准
        self.setFixedSize(40, 22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._anim.valueChanged.connect(lambda v: (setattr(self, "_t", float(v)), self.update()))

    def is_checked(self) -> bool:
        return self._target > 0.5

    def get_t(self) -> float:
        return self._t

    def set_t(self, v: float):
        self._t = float(v)
        self.update()

    t = Property(float, get_t, set_t)

    def setChecked(self, on: bool, animate=True):
        target = 1.0 if on else 0.0
        self._target = target
        if animate and abs(target - self._t) > 1e-6:
            self._anim.stop()
            self._anim.setStartValue(self._t)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._anim.stop()
            self._t = target
            self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            nxt = not self.is_checked()
            self.setChecked(nxt)
            self.toggled.emit(nxt)
        super().mousePressEvent(e)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        h = self.height()
        r = h / 2.0
        track = QRectF(0, 0, self.width(), h)
        p.setPen(Qt.PenStyle.NoPen)
        on_c = QColor(theme.BLUE)
        on_c.setAlphaF(0.30 + 0.62 * self._t)
        off = QColor(20, 24, 32, 34)
        p.setBrush(on_c if self._t > 0.01 else off)
        p.drawRoundedRect(track, r, r)

        d = h - 6
        x = 3 + (self.width() - 6 - d) * self._t
        p.setBrush(QColor("#FFFFFF") if self._t > 0.5 else theme.qcolor("rgba(20,24,32,0.30)"))
        p.drawEllipse(QRectF(x, 3, d, d))
        p.end()


# ------------------------------------------------------------------ 窗口按钮
class WindowButton(QPushButton):
    def __init__(self, icon, hover_bg=None, hover_fg=None, parent=None):
        super().__init__(parent)
        self.icon_name = icon
        self.hover_bg = hover_bg or "rgba(20,24,32,0.08)"
        self.hover_fg = hover_fg or "#14181F"
        self._hover = False
        self.setFixedSize(34, 26)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

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
            p.setBrush(theme.qcolor(self.hover_bg))
            p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 6, 6)
        col = self.hover_fg if self._hover else theme.TXT_2
        draw_icon(p, self.icon_name, QRectF(0, 0, self.width(), self.height()), col, 1.4)
        p.end()


# ------------------------------------------------------------------ 组合件
def card_header(title: str, sub: str = "", right: QWidget = None) -> QWidget:
    """卡片标题行"""
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(10)
    box = QWidget()
    vb = QVBoxLayout(box)
    vb.setContentsMargins(0, 0, 0, 0)
    vb.setSpacing(2)
    t = QLabel(title)
    t.setObjectName("card_title")
    vb.addWidget(t)
    if sub:
        s = QLabel(sub)
        s.setObjectName("card_sub")
        vb.addWidget(s)
    lay.addWidget(box)
    lay.addStretch(1)
    if right is not None:
        lay.addWidget(right, 0, Qt.AlignmentFlag.AlignVCenter)
    return w


class ToggleRow(QWidget):
    """设置项：标题 + 说明 + 开关"""

    def __init__(self, title, desc="", checked=False, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        box = QWidget()
        vb = QVBoxLayout(box)
        vb.setContentsMargins(0, 0, 0, 0)
        vb.setSpacing(3)
        t = QLabel(title)
        t.setStyleSheet(f"color:{theme.TXT_1};font-size:12.5px;font-weight:500;")
        vb.addWidget(t)
        self.desc = None
        if desc:
            self.desc = QLabel(desc)
            self.desc.setObjectName("card_sub")
            vb.addWidget(self.desc)
        lay.addWidget(box, 1)

        self.sw = Switch(checked)
        lay.addWidget(self.sw, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_desc(self, text: str):
        """更新说明文字（如空闲阈值随配置变化）"""
        if self.desc:
            self.desc.setText(text)
