# -*- coding: utf-8 -*-
"""24×24 网格描边图标，与设计稿图标库一致（1.6px 圆头圆角描边）"""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from app import theme

_P = {
    # ---- 导航 ----
    "grid":     [("r", 3, 3, 7.5, 7.5, 1.6), ("r", 13.5, 3, 7.5, 7.5, 1.6),
                 ("r", 3, 13.5, 7.5, 7.5, 1.6), ("r", 13.5, 13.5, 7.5, 7.5, 1.6)],
    "gamepad":  [("r", 2.5, 7.5, 19, 11, 4.5), ("l", 7.6, 11.4, 7.6, 14.6),
                 ("l", 5.6, 13, 9.6, 13), ("c", 15.8, 12.4, 1.15), ("c", 18.3, 14.4, 1.15)],
    "chart":    [("l", 5, 20, 5, 12), ("l", 12, 20, 12, 5), ("l", 19, 20, 19, 14),
                 ("l", 3, 21, 21, 21)],
    "settings": [("c", 12, 12, 8.2), ("c", 12, 12, 3.1),
                 ("l", 12, 3.8, 12, 6.2), ("l", 12, 17.8, 12, 20.2),
                 ("l", 4.9, 7.1, 6.6, 8.8), ("l", 17.4, 15.2, 19.1, 16.9),
                 ("l", 4.9, 16.9, 6.6, 15.2), ("l", 17.4, 8.8, 19.1, 7.1)],
    "search":   [("c", 10.6, 10.6, 6.2), ("l", 15.2, 15.2, 20, 20)],
    # ---- 窗口控制 ----
    "min":      [("l", 6.5, 12, 17.5, 12)],
    "max":      [("r", 6.5, 6.5, 11, 11, 1)],
    "close":    [("l", 6.5, 6.5, 17.5, 17.5), ("l", 17.5, 6.5, 6.5, 17.5)],
}


def draw_icon(painter: QPainter, name: str, rect: QRectF, color: str, width: float = 1.6):
    """在 rect 内按比例绘制 24×24 图标"""
    if name not in _P:
        return
    s = min(rect.width(), rect.height()) / 24.0
    ox = rect.x() + (rect.width() - 24 * s) / 2.0
    oy = rect.y() + (rect.height() - 24 * s) / 2.0

    c = theme.qcolor(color)
    pen = QPen(c, width * s)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    def X(v): return ox + v * s
    def Y(v): return oy + v * s

    for prim in _P[name]:
        k = prim[0]
        if k == "l":
            painter.drawLine(X(prim[1]), Y(prim[2]), X(prim[3]), Y(prim[4]))
        elif k == "c":
            d = prim[3] * 2 * s
            painter.drawEllipse(QRectF(X(prim[1]) - d / 2, Y(prim[2]) - d / 2, d, d))
        elif k == "r":
            painter.drawRoundedRect(QRectF(X(prim[1]), Y(prim[2]), prim[3] * s, prim[4] * s),
                                    prim[5] * s, prim[5] * s)
        elif k == "p":
            path = QPainterPath()
            pts = prim[1]
            path.moveTo(X(pts[0][0]), Y(pts[0][1]))
            for p in pts[1:]:
                path.lineTo(X(p[0]), Y(p[1]))
            if prim[2]:
                path.closeSubpath()
            painter.drawPath(path)


class Icon(QWidget):
    """独立图标控件"""

    def __init__(self, name: str, size: int = 16, color: str = None, width: float = 1.6,
                 parent=None):
        super().__init__(parent)
        # 注意：不要命名为 self.width，会覆盖 QWidget.width() 方法
        self.name, self.color, self.pen_width = name, color or theme.TXT_2, width
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_icon(p, self.name, QRectF(0, 0, self.width(), self.height()),
                  self.color, self.pen_width)
        p.end()
