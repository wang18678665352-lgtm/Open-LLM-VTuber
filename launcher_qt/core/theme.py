"""深色主题调色板、全局 QSS 与 Windows 原生窗口装饰。"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase

IS_WIN = sys.platform.startswith("win")

PALETTE: dict[str, str] = {
    "bg": "#17171f",
    "sidebar": "#121219",
    "panel": "#1f1f2b",
    "panel_alt": "#262636",
    "fg": "#e8e8f2",
    "subtle": "#9a9ab2",
    "accent": "#3b82f6",
    "accent_hover": "#5c9bff",
    "accent_press": "#2f6ed4",
    "danger": "#e5484d",
    "danger_hover": "#f06a6e",
    "ok": "#4cc38a",
    "warn": "#e5c07b",
    "err": "#e06c75",
    "info": "#56c8d8",
    "debug": "#6b7280",
    "console_bg": "#0f0f16",
    "console_fg": "#d5d5e2",
    "border": "#2c2c3c",
    "launcher": "#7aa2f7",
    "entry_bg": "#14141d",
    "tray_border": "#3a3a4d",
}


def color(key: str) -> QColor:
    return QColor(PALETTE[key])


def pick_font(candidates: tuple[str, ...], fallback: str) -> str:
    """返回系统里实际存在的第一个字体名（保证界面不糊、不缺字）。"""
    families = set(QFontDatabase.families())
    for name in candidates:
        if name in families:
            return name
    return fallback


def ui_font_family() -> str:
    return pick_font(
        ("Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI Variable Text", "Segoe UI"),
        QFont().defaultFamily(),
    )


def mono_font_family() -> str:
    return pick_font(
        ("Cascadia Mono", "Consolas", "JetBrains Mono", "Courier New"), "Courier New"
    )


def build_stylesheet() -> str:
    p = PALETTE
    return f"""
* {{
    outline: 0;
}}
QWidget {{
    background: {p["bg"]};
    color: {p["fg"]};
    font-family: "{ui_font_family()}";
    font-size: 10pt;
}}
QMainWindow, QDialog {{
    background: {p["bg"]};
}}
QToolTip {{
    background: {p["panel_alt"]};
    color: {p["fg"]};
    border: 1px solid {p["border"]};
    padding: 6px 8px;
}}

/* ---------- 侧边栏 ---------- */
#sidebar {{
    background: {p["sidebar"]};
    border-right: 1px solid {p["border"]};
}}
#sidebarTitle {{
    color: {p["fg"]};
    font-size: 14pt;
    font-weight: 600;
    background: transparent;
}}
#sidebarSub {{
    color: {p["subtle"]};
    font-size: 9pt;
    background: transparent;
}}
#navButton {{
    background: transparent;
    color: {p["fg"]};
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-size: 10.5pt;
}}
#navButton:hover {{
    background: {p["panel_alt"]};
}}
#navButton:checked {{
    background: {p["accent"]};
    color: #ffffff;
    font-weight: 600;
}}
#statusDot {{
    color: {p["subtle"]};
    font-size: 13pt;
    background: transparent;
}}
#statusText {{
    color: {p["subtle"]};
    font-size: 9pt;
    background: transparent;
}}

/* ---------- 卡片与文字 ---------- */
#card {{
    background: {p["panel"]};
    border: 1px solid {p["border"]};
    border-radius: 10px;
}}
#pageTitle {{
    color: {p["fg"]};
    font-size: 16pt;
    font-weight: 700;
}}
#cardTitle {{
    color: {p["fg"]};
    font-size: 11pt;
    font-weight: 600;
    background: transparent;
}}
#hint, #cardHint {{
    color: {p["subtle"]};
    background: transparent;
}}
#cardLabel {{
    color: {p["fg"]};
    background: transparent;
}}
#bigState {{
    color: {p["fg"]};
    font-size: 12pt;
    font-weight: 600;
    background: transparent;
}}

/* ---------- 按钮 ---------- */
QPushButton {{
    background: {p["panel_alt"]};
    color: {p["fg"]};
    border: 1px solid {p["border"]};
    border-radius: 8px;
    padding: 7px 14px;
}}
QPushButton:hover {{
    background: {p["border"]};
}}
QPushButton:pressed {{
    background: {p["panel"]};
}}
QPushButton:disabled {{
    background: {p["panel"]};
    color: {p["subtle"]};
    border-color: {p["panel"]};
}}
QPushButton[variant="accent"] {{
    background: {p["accent"]};
    color: #ffffff;
    border: 1px solid {p["accent"]};
    font-weight: 600;
}}
QPushButton[variant="accent"]:hover {{
    background: {p["accent_hover"]};
    border-color: {p["accent_hover"]};
}}
QPushButton[variant="accent"]:pressed {{
    background: {p["accent_press"]};
}}
QPushButton[variant="launch"] {{
    background: {p["accent"]};
    color: #ffffff;
    border: none;
    border-radius: 12px;
    font-size: 16pt;
    font-weight: 700;
    padding: 28px 36px;
}}
QPushButton[variant="launch"]:hover {{
    background: {p["accent_hover"]};
}}
QPushButton[variant="launch"]:pressed {{
    background: {p["accent_press"]};
}}
QPushButton[variant="launchStop"] {{
    background: {p["danger"]};
    color: #ffffff;
    border: none;
    border-radius: 12px;
    font-size: 16pt;
    font-weight: 700;
    padding: 28px 36px;
}}
QPushButton[variant="launchStop"]:hover {{
    background: {p["danger_hover"]};
}}

/* ---------- 输入控件 ---------- */
QLineEdit {{
    background: {p["entry_bg"]};
    color: {p["fg"]};
    border: 1px solid {p["border"]};
    border-radius: 6px;
    padding: 6px 8px;
    selection-background-color: {p["accent"]};
}}
QLineEdit:focus {{
    border-color: {p["accent"]};
}}
QCheckBox {{
    background: transparent;
    color: {p["fg"]};
    spacing: 8px;
}}
QCheckBox:disabled {{
    color: {p["subtle"]};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid {p["tray_border"]};
    background: {p["entry_bg"]};
}}
QCheckBox::indicator:hover {{
    border-color: {p["accent"]};
}}
QCheckBox::indicator:checked {{
    background: {p["accent"]};
    border-color: {p["accent"]};
}}

/* ---------- 控制台 ---------- */
#console {{
    background: {p["console_bg"]};
    color: {p["console_fg"]};
    border: 1px solid {p["border"]};
    border-radius: 8px;
    padding: 6px;
    font-family: "{mono_font_family()}";
    font-size: 9.5pt;
    selection-background-color: {p["accent"]};
}}
#envInfo {{
    background: {p["panel"]};
    color: {p["fg"]};
    border: none;
    font-family: "{mono_font_family()}";
    font-size: 9.5pt;
}}

/* ---------- 表格 ---------- */
QTreeWidget {{
    background: {p["panel"]};
    alternate-background-color: {p["panel_alt"]};
    color: {p["fg"]};
    border: 1px solid {p["border"]};
    border-radius: 8px;
    gridline-color: {p["border"]};
}}
QTreeWidget::item {{
    padding: 5px 4px;
}}
QTreeWidget::item:selected {{
    background: {p["accent"]};
    color: #ffffff;
}}
QHeaderView::section {{
    background: {p["panel_alt"]};
    color: {p["fg"]};
    border: none;
    border-right: 1px solid {p["border"]};
    border-bottom: 1px solid {p["border"]};
    padding: 7px 6px;
    font-weight: 600;
}}

/* ---------- 滚动条 ---------- */
QScrollBar:vertical {{
    background: transparent;
    width: 12px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {p["tray_border"]};
    border-radius: 5px;
    min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{
    background: {p["subtle"]};
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 12px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {p["tray_border"]};
    border-radius: 5px;
    min-width: 28px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0px;
    width: 0px;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
}}

/* ---------- 菜单（托盘） ---------- */
QMenu {{
    background: {p["panel"]};
    color: {p["fg"]};
    border: 1px solid {p["border"]};
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 18px;
    border-radius: 6px;
}}
QMenu::item:selected {{
    background: {p["accent"]};
    color: #ffffff;
}}
QMenu::separator {{
    height: 1px;
    background: {p["border"]};
    margin: 4px 6px;
}}
"""


# ---------------------------------------------------------------------------
# Windows 原生窗口装饰：深色标题栏 + Win11 圆角
# ---------------------------------------------------------------------------

_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWCP_ROUND = 2


def apply_native_chrome(widget, dark: bool = True) -> None:
    """让 Win10/11 的原生标题栏跟随深色主题，并启用 Win11 圆角。

    必须在窗口 ``show()`` 之后调用；失败时静默忽略（不影响功能）。
    """
    if not IS_WIN:
        return
    try:
        import ctypes

        hwnd = int(widget.winId())
        dwmapi = ctypes.windll.dwmapi
        value = ctypes.c_int(1 if dark else 0)
        dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd),
            ctypes.c_uint(_DWMWA_USE_IMMERSIVE_DARK_MODE),
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
        corner = ctypes.c_int(_DWMWCP_ROUND)
        dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd),
            ctypes.c_uint(_DWMWA_WINDOW_CORNER_PREFERENCE),
            ctypes.byref(corner),
            ctypes.sizeof(corner),
        )
    except Exception:  # noqa: BLE001
        pass


def set_app_user_model_id(app_id: str) -> None:
    """设置任务栏分组标识，避免启动器被并入 python.exe 分组。"""
    if not IS_WIN:
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:  # noqa: BLE001
        pass


def high_dpi_rounding_policy():
    """Qt6 高 DPI 舍入策略：跟随系统缩放，不取整（避免 125% 缩放下界面发虚）。"""
    from PySide6.QtGui import QGuiApplication

    return QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
