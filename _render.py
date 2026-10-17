# -*- coding: utf-8 -*-
"""把三个界面渲染成 PNG 预览图"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication  # noqa: E402

from app import theme  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "preview")


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
