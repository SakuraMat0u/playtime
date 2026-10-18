# -*- coding: utf-8 -*-
"""
设计令牌 —— 与画布设计稿 1:1 对齐
Playtime · 游戏时长统计
"""
from PySide6.QtGui import QColor, QFont

# ---------------------------------------------------------------- 调色板（灰白亮色主题）
BG            = "#ECEEF2"          # 主背景（灰白）
CYAN          = "#13DDC4"
BLUE          = "#2EA7FF"
PURPLE        = "#9381FF"
RED           = "#FF4D6D"
ORANGE        = "#FFB454"

TXT_1         = "rgba(20,24,32,0.90)"   # 主文字
TXT_2         = "rgba(20,24,32,0.55)"   # 次级文字
TXT_3         = "rgba(20,24,32,0.38)"   # 弱文字 / 占位符

CARD_BG       = "rgba(255,255,255,0.78)"  # 卡片底色（浅底上的白卡）
CARD_LINE     = "rgba(20,24,32,0.10)"   # 卡片描边 1px
FIELD_BG      = "rgba(20,24,32,0.04)"   # 输入框
FIELD_LINE    = "rgba(20,24,32,0.10)"
DIVIDER       = "rgba(20,24,32,0.08)"

# ---------------------------------------------------------------- 圆角
R_CARD = 16   # 卡片
R_PILL = 12   # 按钮 / 输入框 / 胶囊
R_NAV  = 10   # 导航项
R_SM   = 8    # 小标签

# ---------------------------------------------------------------- 尺寸
WIN_W, WIN_H   = 1280, 800
TITLEBAR_H     = 40
SIDEBAR_W      = 240
TOPBAR_H       = 64
RIGHT_W        = 300
STATUS_H       = 32
PAD_CONTENT    = 24
GAP            = 16

# ---------------------------------------------------------------- 字体
_UI_FAMILIES  = ["Inter", "Noto Sans SC", "Microsoft YaHei", "PingFang SC", "Segoe UI"]
_MONO_FAMILIES = ["JetBrains Mono", "Noto Sans SC", "Consolas", "Microsoft YaHei"]


def qcolor(s: str) -> QColor:
    """解析主题色值（#RRGGBB / rgba(r,g,b,a)）为 QColor。

    QColor 的字符串构造不支持 rgba()，直接传会得到无效的纯黑，
    所有把主题色喂给 QPainter/QColor 的地方都必须走这里。
    """
    s = s.strip()
    if s.startswith(("rgba(", "rgb(")):
        parts = s[s.index("(") + 1: s.rindex(")")].split(",")
        r, g, b = (int(float(x)) for x in parts[:3])
        a = int(float(parts[3]) * 255) if len(parts) > 3 else 255
        return QColor(r, g, b, a)
    return QColor(s)


def ui(size: float, weight=QFont.Weight.Medium) -> QFont:
    f = QFont()
    f.setFamilies(_UI_FAMILIES)
    f.setPointSizeF(size)
    f.setWeight(weight)
    return f


def mono(size: float, weight=QFont.Weight.Medium) -> QFont:
    f = QFont()
    f.setFamilies(_MONO_FAMILIES)
    f.setPointSizeF(size)
    f.setWeight(weight)
    return f


Regular  = QFont.Weight.Normal
Medium   = QFont.Weight.Medium
SemiBold = QFont.Weight.DemiBold
Bold     = QFont.Weight.Bold


# ---------------------------------------------------------------- 全局样式
def stylesheet() -> str:
    return f"""
QWidget {{
    background: transparent;
    color: {TXT_1};
    font-family: "Inter","Noto Sans SC","Microsoft YaHei","PingFang SC","Segoe UI";
}}
QWidget#root {{
    background-color: {BG};
    border: 1px solid rgba(20,24,32,0.08);
}}
QFrame#card {{
    background-color: {CARD_BG};
    border: 1px solid {CARD_LINE};
    border-radius: {R_CARD}px;
}}
QFrame#divider_h {{ background-color: {DIVIDER}; max-height: 1px; min-height: 1px; }}
QFrame#divider_v {{ background-color: {DIVIDER}; max-width: 1px; min-width: 1px; }}

QLabel#card_title {{ color: {TXT_1}; font-size: 13px; font-weight: 600; }}
QLabel#card_sub   {{ color: {TXT_2}; font-size: 11px; }}
QLabel#kpi_label  {{ color: {TXT_2}; font-size: 12px; }}
QLabel#kpi_unit   {{ color: {TXT_3}; font-size: 11px; }}
QLabel#sec_label  {{ color: {TXT_3}; font-size: 11px; font-weight: 600; }}
QLabel#page_title {{ color: {TXT_1}; font-size: 20px; font-weight: 600; }}
QLabel#status     {{ color: {TXT_3}; font-size: 11px; }}
QLabel#muted      {{ color: {TXT_2}; font-size: 12px; }}

QLineEdit {{
    background-color: {FIELD_BG};
    border: 1px solid {FIELD_LINE};
    border-radius: {R_PILL}px;
    padding: 0 12px;
    height: 34px;
    color: {TXT_1};
    font-size: 12px;
    selection-background-color: {BLUE};
}}
QLineEdit:focus {{ border: 1px solid rgba(46,167,255,0.55); }}
QLineEdit::placeholder {{ color: {TXT_3}; }}

QPushButton#primary {{
    background-color: {BLUE};
    color: #06121F;
    border: none;
    border-radius: {R_PILL}px;
    height: 34px;
    padding: 0 16px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton#primary:hover   {{ background-color: #47B3FF; }}
QPushButton#primary:pressed {{ background-color: #1E93EA; }}

QPushButton#ghost {{
    background-color: rgba(20,24,32,0.04);
    color: {TXT_1};
    border: 1px solid {CARD_LINE};
    border-radius: {R_PILL}px;
    height: 34px;
    padding: 0 14px;
    font-size: 12px;
}}
QPushButton#ghost:hover {{ background-color: rgba(20,24,32,0.08); }}

QPushButton#danger {{
    background-color: rgba(255,77,109,0.12);
    color: {RED};
    border: 1px solid rgba(255,77,109,0.28);
    border-radius: {R_PILL}px;
    height: 34px;
    padding: 0 14px;
    font-size: 12px;
}}
QPushButton#danger:hover {{ background-color: rgba(255,77,109,0.2); }}

QPushButton#pill {{
    background-color: rgba(20,24,32,0.04);
    color: {TXT_2};
    border: 1px solid {CARD_LINE};
    border-radius: {R_SM}px;
    height: 28px;
    padding: 0 12px;
    font-size: 11px;
}}
QPushButton#pill:hover  {{ color: {TXT_1}; background-color: rgba(20,24,32,0.08); }}
QPushButton#pill[on="true"] {{
    background-color: rgba(46,167,255,0.14);
    border: 1px solid rgba(46,167,255,0.4);
    color: #7FC6FF;
}}

QPushButton#seg {{
    background-color: transparent;
    color: {TXT_2};
    border: none;
    border-radius: {R_SM}px;
    height: 28px;
    padding: 0 14px;
    font-size: 12px;
}}
QPushButton#seg:hover {{ color: {TXT_1}; }}
QPushButton#seg[on="true"] {{
    background-color: rgba(20,24,32,0.06);
    color: {TXT_1};
    font-weight: 600;
}}

QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{
    background: transparent; width: 8px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: rgba(20,24,32,0.18); border-radius: 4px; min-height: 40px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ height: 0; }}
QToolTip {{
    background-color: #FFFFFF; color: {TXT_1};
    border: 1px solid {CARD_LINE}; border-radius: 6px; padding: 4px 8px;
}}
"""


def fmt_hms(seconds: int) -> str:
    """秒 -> HH:MM:SS"""
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
