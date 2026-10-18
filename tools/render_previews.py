# -*- coding: utf-8 -*-
"""把三个界面渲染成 PNG 预览图（开发用，离屏运行，不弹窗口）

用法： python tools/render_previews.py [--out <目录>]
输出： <仓库根>/preview/*.png（或 --out 指定目录）
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

from app import theme  # noqa: E402


def _out_dir() -> Path:
    for i, a in enumerate(sys.argv):
        if a == "--out" and i + 1 < len(sys.argv):
            return Path(sys.argv[i + 1])
    return ROOT / "preview"


OUT = _out_dir()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(theme.stylesheet())

    from main import MainWindow, load_fonts
    load_fonts()
    w = MainWindow()
    w.ctx.monitor.stop()          # 预览不需要后台轮询
    w.resize(1280, 800)
    os.makedirs(OUT, exist_ok=True)

    for key, name in (("library", "01-游戏库"), ("analytics", "02-统计分析"),
                      ("settings", "03-设置")):
        w.goto(key)
        app.processEvents()
        w.grab().save(os.path.join(OUT, f"{name}.png"), "PNG")
        print("saved", name)

    return 0


if __name__ == "__main__":
    sys.exit(main())
