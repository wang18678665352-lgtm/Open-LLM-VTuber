"""Open-LLM-VTuber 原生启动器（PySide6 / Qt6）。

与本仓库根目录下的 ``launcher.py``（tkinter 旧版）功能对齐，
但改用 Qt6 原生窗口、原生控件与原生菜单，并可打包为单文件 exe。
"""

from __future__ import annotations

APP_NAME = "Open-LLM-VTuber 启动器"
APP_VERSION = "1.3.0"
GITHUB_URL = "https://github.com/Open-LLM-VTuber/Open-LLM-VTuber"
DOCS_URL = "https://open-llm-vtuber.github.io/"

__all__ = ["APP_NAME", "APP_VERSION", "GITHUB_URL", "DOCS_URL"]
