# -*- coding: utf-8 -*-
"""自绘图表 / 背景光晕 —— 对应设计稿中的柱状图、环形图与 aurora 底纹"""
from PySide6.QtCore import QRectF, Qt, QPointF
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

from app import theme


def _q(color: str) -> QColor:
    return QColor(color)


class AuroraBackdrop(QWidget):
    """背景极光：青 → 紫 → 蓝 三处径向光晕"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, _):
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(0, 0, w, h, _q(theme.BG))

        blobs = [
            (-w * 0.10, -h * 0.28, w * 0.78, theme.CYAN, 0.06),
            (w * 0.72, -h * 0.10, w * 0.70, theme.PURPLE, 0.05),
            (w * 0.30, h * 0.92, w * 0.90, theme.BLUE, 0.04),
        ]
        for cx, cy, r, color, a in blobs:
            g = QRadialGradient(QPointF(cx, cy), r)
            c = _q(color)
            c.setAlphaF(a)
            c2 = QColor(c)
            c2.setAlphaF(0.0)
            g.setColorAt(0.0, c)
            g.setColorAt(0.55, QColor(c.red(), c.green(), c.blue(), int(a * 90)))
            g.setColorAt(1.0, c2)
            p.fillRect(0, 0, w, h, g)
        p.end()


class BarChart(QWidget):
    """柱状图：圆角柱体 + 顶部渐变，支持高亮当前项"""

    def __init__(self, data, accent=None, highlight=-1, show_labels=True, parent=None):
        """
        data: [(label, value), ...]
        """
        super().__init__(parent)
        self.data = list(data)
        self.accent = accent or theme.CYAN
        self.highlight = highlight
        self.show_labels = show_labels
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumHeight(60)

    def set_data(self, data, highlight=-1):
        self.data = list(data)
        self.highlight = highlight
        self.update()

    def paintEvent(self, _):
        if not self.data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        label_h = 16 if self.show_labels else 0
        top = 4
        bottom = self.height() - label_h - 2
        usable_h = max(8, bottom - top)
        vmax = max(v for _, v in self.data) or 1.0

        n = len(self.data)
        slot = self.width() / float(n)
        bar_w = min(slot * 0.56, 14.0) if n > 12 else min(slot * 0.5, 22.0)

        # 基线
        pen = QPen(QColor(20, 24, 32, 26), 1)
        p.setPen(pen)
        p.drawLine(QPointF(0, bottom + 1.5), QPointF(self.width(), bottom + 1.5))

        base = _q(self.accent)
        for i, (label, v) in enumerate(self.data):
            cx = slot * (i + 0.5)
            bh = max(2.0, usable_h * (v / vmax))
            r = min(bar_w / 2.0, 4.0)
            rect = QRectF(cx - bar_w / 2.0, bottom - bh, bar_w, bh)

            is_hi = (i == self.highlight)
            g = QLinearGradient(QPointF(0, rect.top()), QPointF(0, rect.bottom()))
            top_c = QColor(base)
            top_c.setAlphaF(1.0 if is_hi else 0.72)
            bot_c = QColor(base)
            bot_c.setAlphaF(0.30 if is_hi else 0.12)
            g.setColorAt(0.0, top_c)
            g.setColorAt(1.0, bot_c)

            path = QPainterPath()
            path.moveTo(rect.left(), rect.bottom())
            path.lineTo(rect.left(), rect.top() + r)
            path.arcTo(QRectF(rect.left(), rect.top(), r * 2, r * 2), 180, -90)
            path.lineTo(rect.right() - r, rect.top())
            path.arcTo(QRectF(rect.right() - r * 2, rect.top(), r * 2, r * 2), 90, -90)
            path.lineTo(rect.right(), rect.bottom())
            path.closeSubpath()
            p.fillPath(path, g)

        if self.show_labels:
            p.setPen(QColor(20, 24, 32, 90))
            p.setFont(theme.ui(9, theme.Medium))
            step = max(1, n // 8)
            for i, (label, v) in enumerate(self.data):
                if i % step and i != n - 1:
                    continue
                cx = slot * (i + 0.5)
                p.drawText(QRectF(cx - slot * 0.6, bottom + 3, slot * 1.2, 13),
                           Qt.AlignmentFlag.AlignCenter, str(label))
        p.end()


class DonutChart(QWidget):
    """环形图：分段圆头弧 + 中心数值"""

    def __init__(self, segments, center_value="", center_label="", thickness=18, parent=None):
        """
        segments: [(value, color, name), ...]
        """
        super().__init__(parent)
        self.segments = list(segments)
        self.center_value = center_value
        self.center_label = center_label
        self.thickness = thickness
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_segments(self, segments, center_value=None, center_label=None):
        self.segments = list(segments)
        if center_value is not None:
            self.center_value = center_value
        if center_label is not None:
            self.center_label = center_label
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height())
        pad = self.thickness / 2.0 + 2
        box = QRectF((self.width() - side) / 2.0 + pad, (self.height() - side) / 2.0 + pad,
                     side - pad * 2, side - pad * 2)

        total = sum(v for v, _, _ in self.segments) or 1.0

        # 轨道
        p.setPen(QPen(QColor(20, 24, 32, 16), self.thickness))
        p.drawEllipse(box)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        angle = 90.0 * 16.0  # 12 点方向起笔
        p.setCapStyle = None
        cap = QPen()
        cap.setCapStyle(Qt.PenCapStyle.FlatCap)

        for v, color, _ in self.segments:
            span = (v / total) * 360.0 * 16.0
            gap = 2.2 * 16.0
            pen = QPen(_q(color), self.thickness)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.drawArc(box, int(angle + gap / 2), int(max(span - gap, 1)))
            angle += span

        # 中心
        p.setPen(Qt.PenStyle.NoPen)
        cy = box.center().y()
        if self.center_value:
            p.setPen(QColor(20, 24, 32, 235))
            p.setFont(theme.mono(19, theme.SemiBold))
            p.drawText(QRectF(0, cy - 20, self.width(), 24), Qt.AlignmentFlag.AlignCenter,
                       self.center_value)
        if self.center_label:
            p.setPen(QColor(20, 24, 32, 110))
            p.setFont(theme.ui(10, theme.Medium))
            p.drawText(QRectF(0, cy + 4, self.width(), 16), Qt.AlignmentFlag.AlignCenter,
                       self.center_label)
        p.end()


class ProgressBar(QWidget):
    """细长进度条"""

    def __init__(self, value=0.0, accent=None, height=6, parent=None):
        super().__init__(parent)
        self._value = value
        self.accent = accent or theme.BLUE
        self.setFixedHeight(height)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def set_value(self, v: float):
        self._value = max(0.0, min(1.0, v))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.height() / 2.0
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(20, 24, 32, 22))
        p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), r, r)
        p.setBrush(_q(self.accent))
        p.drawRoundedRect(QRectF(0, 0, max(self.width() * self._value, self.height()),
                                 self.height()), r, r)
        p.end()


class StatusDot(QWidget):
    """状态圆点（带呼吸光晕）"""

    def __init__(self, color=None, size=7, glow=True, parent=None):
        super().__init__(parent)
        self.color = color or theme.CYAN
        self.glow = glow
        d = size + (10 if glow else 0)
        self.setFixedSize(d, d)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = _q(self.color)
        if self.glow:
            g = QRadialGradient(QPointF(self.width() / 2, self.height() / 2), self.width() / 2)
            g.setColorAt(0.0, QColor(c.red(), c.green(), c.blue(), 110))
            g.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), 0))
            p.fillRect(0, 0, self.width(), self.height(), g)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        r = (self.width() - 10) / 2.0 if self.glow else self.width() / 2.0
        p.drawEllipse(QPointF(self.width() / 2, self.height() / 2), r, r)
        p.end()
