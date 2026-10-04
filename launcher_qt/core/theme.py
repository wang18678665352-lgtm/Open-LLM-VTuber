"""深色主题调色板、全局 QSS 与 Windows 原生窗口装饰。"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase

IS_WIN = sys.platform.startswith("win")

PALETTE: dict[str, str] = {
    "bg": "#17171f",
    "window_top": "#1c1c27",
    "window_bottom": "#111119",
    "sidebar": "#121219",
    "sidebar_top": "#171722",
    "panel": "#1f1f2b",
    "panel_top": "#22222f",
    "panel_bottom": "#1b1b26",
    "panel_alt": "#262636",
    "fg": "#e8e8f2",
    "subtle": "#9a9ab2",
    "accent": "#3b82f6",
    "accent_hover": "#5c9bff",
    "accent_press": "#2f6ed4",
    "accent2": "#7c5cf5",
    "danger": "#e5484d",
    "danger_hover": "#f06a6e",
    "ok": "#4cc38a",
    "warn": "#e5c07b",
    "err": "#e06c75",
    "info": "#56c8d8",
    "debug": "#6b7280",
    "console_bg": "#0d0d15",
    "console_fg": "#d5d5e2",
    "border": "#2c2c3c",
    "border_soft": "rgba(255, 255, 255, 0.07)",
    "launcher": "#7aa2f7",
    "entry_bg": "#14141d",
    "tray_border": "#3a3a4d",
    "hero_a": "#243258",
    "hero_b": "#2f2049",
    "hover": "rgba(255, 255, 255, 0.07)",
    "hover_strong": "rgba(255, 255, 255, 0.12)",
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
    ui = ui_font_family()
    mono = mono_font_family()
    assets = _widget_assets()
    return f"""
* {{
    outline: 0;
}}
QWidget {{
    background: transparent;
    color: {p["fg"]};
    font-family: "{ui}";
    font-size: 10pt;
}}
QLabel {{
    background: transparent;
}}
QMainWindow, QDialog {{
    background: {p["window_bottom"]};
}}
QToolTip {{
    background: {p["panel_top"]};
    color: {p["fg"]};
    border: 1px solid {p["border_soft"]};
    border-radius: 6px;
    padding: 6px 9px;
}}

/* ---------- 内容区背景 ---------- */
#content {{
    background: qlineargradient(x1:0, y1:0, x2:0.35, y2:1,
        stop:0 {p["window_top"]}, stop:1 {p["window_bottom"]});
}}

/* ---------- 侧边栏 ---------- */
#sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:0.4, y2:1,
        stop:0 {p["sidebar_top"]}, stop:1 {p["sidebar"]});
    border-right: 1px solid {p["border_soft"]};
}}
#sidebarTitle {{
    color: #ffffff;
    font-size: 12.5pt;
    font-weight: 700;
    background: transparent;
}}
#sidebarSub {{
    color: {p["subtle"]};
    font-size: 8.5pt;
    background: transparent;
}}
#navButton {{
    background: transparent;
    color: {p["subtle"]};
    border: none;
    border-left: 3px solid transparent;
    border-radius: 9px;
    padding: 9px 12px;
    text-align: left;
    font-size: 10.5pt;
}}
#navButton:hover {{
    background: {p["hover"]};
    color: {p["fg"]};
}}
#navButton:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(59, 130, 246, 0.30), stop:1 rgba(124, 92, 245, 0.08));
    border-left: 3px solid {p["accent"]};
    color: #ffffff;
    font-weight: 600;
}}
#statusChip {{
    background: rgba(255, 255, 255, 0.045);
    border: 1px solid {p["border_soft"]};
    border-radius: 9px;
}}
#statusDot {{
    background: {p["subtle"]};
    border-radius: 4px;
    min-width: 8px;
    max-width: 8px;
    min-height: 8px;
    max-height: 8px;
}}
#statusText {{
    color: {p["subtle"]};
    font-size: 9pt;
    background: transparent;
}}

/* ---------- 卡片与文字 ---------- */
#card {{
    background: qlineargradient(x1:0, y1:0, x2:0.25, y2:1,
        stop:0 {p["panel_top"]}, stop:1 {p["panel_bottom"]});
    border: 1px solid {p["border_soft"]};
    border-radius: 12px;
}}
#hero {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {p["hero_a"]}, stop:0.55 #252a4d, stop:1 {p["hero_b"]});
    border: 1px solid rgba(122, 162, 247, 0.22);
    border-radius: 14px;
}}
#pageTitle {{
    color: #ffffff;
    font-size: 15pt;
    font-weight: 700;
    background: transparent;
}}
#pageSub {{
    color: {p["subtle"]};
    font-size: 9.5pt;
    background: transparent;
}}
#cardTitle {{
    color: {p["fg"]};
    font-size: 10.5pt;
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
    color: #ffffff;
    font-size: 15pt;
    font-weight: 700;
    background: transparent;
}}
#chip {{
    background: rgba(0, 0, 0, 0.28);
    border: 1px solid {p["border_soft"]};
    border-radius: 7px;
    color: #cfd6ea;
    font-family: "{mono}";
    font-size: 9.5pt;
    padding: 4px 9px;
}}
#pill {{
    background: rgba(255, 255, 255, 0.10);
    border: 1px solid {p["border_soft"]};
    border-radius: 9px;
    color: #ffffff;
    font-size: 9pt;
    padding: 3px 10px;
}}

/* ---------- 按钮 ---------- */
QPushButton {{
    background: rgba(255, 255, 255, 0.055);
    color: {p["fg"]};
    border: 1px solid {p["border_soft"]};
    border-radius: 9px;
    padding: 7px 14px;
}}
QPushButton:hover {{
    background: {p["hover_strong"]};
    border-color: rgba(255, 255, 255, 0.20);
}}
QPushButton:pressed {{
    background: rgba(0, 0, 0, 0.28);
}}
QPushButton:disabled {{
    background: rgba(255, 255, 255, 0.03);
    color: {p["subtle"]};
    border-color: rgba(255, 255, 255, 0.05);
}}
QPushButton[variant="ghost"] {{
    background: transparent;
    border: 1px solid transparent;
    color: {p["subtle"]};
    padding: 6px 10px;
}}
QPushButton[variant="ghost"]:hover {{
    background: {p["hover"]};
    color: {p["fg"]};
}}
QPushButton[variant="accent"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {p["accent"]}, stop:1 {p["accent2"]});
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.16);
    font-weight: 600;
    padding: 8px 16px;
}}
QPushButton[variant="accent"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {p["accent_hover"]}, stop:1 #8f74ff);
}}
QPushButton[variant="accent"]:pressed {{
    background: {p["accent_press"]};
}}
QPushButton[variant="launch"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #4f8cf7, stop:0.55 #4a7bf6, stop:1 #6d5cf0);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.22);
    border-radius: 14px;
    font-size: 16pt;
    font-weight: 700;
    padding: 26px 34px;
}}
QPushButton[variant="launch"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #62a0ff, stop:0.55 #5b8bff, stop:1 #8168ff);
}}
QPushButton[variant="launch"]:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #3d76dd, stop:1 #5b4bd8);
}}
QPushButton[variant="launchStop"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #f05a60, stop:0.55 #e8484d, stop:1 #d8407a);
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.22);
    border-radius: 14px;
    font-size: 16pt;
    font-weight: 700;
    padding: 26px 34px;
}}
QPushButton[variant="launchStop"]:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #ff6f75, stop:1 #ec5590);
}}
QPushButton[variant="launchStop"]:pressed {{
    background: #c93f44;
}}

/* ---------- 输入控件 ---------- */
QLineEdit {{
    background: {p["entry_bg"]};
    color: {p["fg"]};
    border: 1px solid {p["border_soft"]};
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: {p["accent"]};
}}
QLineEdit:hover {{
    border-color: rgba(255, 255, 255, 0.18);
}}
QLineEdit:focus {{
    border-color: {p["accent"]};
    background: #16161f;
}}
QCheckBox {{
    background: transparent;
    color: {p["fg"]};
    spacing: 8px;
}}
QCheckBox:hover {{
    color: #ffffff;
}}
QCheckBox:disabled {{
    color: {p["subtle"]};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 5px;
    border: 1px solid {p["tray_border"]};
    background: {p["entry_bg"]};
}}
QCheckBox::indicator:hover {{
    border-color: {p["accent"]};
}}
QCheckBox::indicator:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {p["accent"]}, stop:1 {p["accent2"]});
    border-color: rgba(255, 255, 255, 0.35);
}}
QCheckBox::indicator:checked:disabled {{
    background: {p["tray_border"]};
}}

/* ---------- 控制台 / 环境信息 ---------- */
#console {{
    background: {p["console_bg"]};
    color: {p["console_fg"]};
    border: 1px solid {p["border_soft"]};
    border-radius: 10px;
    padding: 8px 10px;
    font-family: "{mono}";
    font-size: 9.5pt;
    selection-background-color: {p["accent"]};
}}
#envInfo {{
    background: rgba(0, 0, 0, 0.22);
    color: {p["fg"]};
    border: 1px solid {p["border_soft"]};
    border-radius: 10px;
    padding: 8px 10px;
    font-family: "{mono}";
    font-size: 9.5pt;
}}

/* ---------- 表格 ---------- */
QTreeWidget {{
    background: rgba(0, 0, 0, 0.22);
    alternate-background-color: rgba(255, 255, 255, 0.028);
    color: {p["fg"]};
    border: 1px solid {p["border_soft"]};
    border-radius: 10px;
    padding: 4px;
}}
QTreeWidget::item {{
    padding: 7px 4px;
    border: none;
}}
QTreeWidget::item:selected {{
    background: rgba(59, 130, 246, 0.22);
    color: #ffffff;
}}
QHeaderView::section {{
    background: transparent;
    color: {p["subtle"]};
    border: none;
    border-bottom: 1px solid {p["border_soft"]};
    padding: 7px 6px;
    font-weight: 600;
}}

/* ---------- 滚动条 ---------- */
QScrollBar:vertical {{
    background: transparent;
    width: 11px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: rgba(255, 255, 255, 0.16);
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(255, 255, 255, 0.30);
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 11px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: rgba(255, 255, 255, 0.16);
    border-radius: 5px;
    min-width: 30px;
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
    background: {p["panel_top"]};
    color: {p["fg"]};
    border: 1px solid {p["border_soft"]};
    border-radius: 10px;
    padding: 5px;
}}
QMenu::item {{
    padding: 7px 20px;
    border-radius: 7px;
}}
QMenu::item:selected {{
    background: rgba(59, 130, 246, 0.30);
    color: #ffffff;
}}
QMenu::separator {{
    height: 1px;
    background: {p["border_soft"]};
    margin: 5px 8px;
}}
""" + _form_rules(p, assets)


# ---------------------------------------------------------------------------
# 运行时渲染的小图像（开关、下拉箭头）
# ---------------------------------------------------------------------------
_WIDGET_ASSETS: dict[str, str] | None = None


def _widget_assets() -> dict[str, str]:
    """把开关与下拉箭头画成 PNG 放到临时目录，供 QSS 的 image: url() 引用。

    QSS 不支持内联 SVG/绘制代码，用运行时渲染既保持了矢量观感，
    又不需要往仓库里塞二进制资源。
    """
    global _WIDGET_ASSETS
    if _WIDGET_ASSETS is not None:
        return _WIDGET_ASSETS
    result: dict[str, str] = {}
    try:
        import tempfile
        from pathlib import Path

        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QGuiApplication, QPainter, QPainterPath, QPen, QPixmap

        if QGuiApplication.instance() is None:
            return result
        out_dir = Path(tempfile.gettempdir()) / "open-llm-vtuber-launcher"
        out_dir.mkdir(parents=True, exist_ok=True)

        def save(name: str, pixmap: QPixmap) -> None:
            target = out_dir / name
            if pixmap.save(str(target), "PNG"):
                result[name.split(".")[0]] = target.as_posix()

        # 开关：关 / 开
        for state in (False, True):
            scale = 2
            width, height = 38 * scale, 21 * scale
            pixmap = QPixmap(width, height)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(Qt.PenStyle.NoPen)
            track = QColor(PALETTE["accent"] if state else "#3a3a4d")
            painter.setBrush(track)
            radius = (height - 4) / 2
            painter.drawRoundedRect(QRectF(2, 2, width - 4, height - 4), radius, radius)
            knob = height - 10
            left = (width - 5 - knob) if state else 5
            painter.setBrush(QColor("#ffffff" if state else "#8f8fa6"))
            painter.drawEllipse(QRectF(left, 5, knob, knob))
            painter.end()
            save(f"switch_{'on' if state else 'off'}.png", pixmap)

        # 下拉箭头
        scale = 3
        size = 24 * scale
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(QColor(PALETTE["subtle"]))
        pen.setWidthF(2.4 * scale)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        path = QPainterPath()
        path.moveTo(7.4 * scale, 10.0 * scale)
        path.lineTo(12.0 * scale, 14.6 * scale)
        path.lineTo(16.6 * scale, 10.0 * scale)
        painter.drawPath(path)
        painter.end()
        save("chevron.png", pixmap)
    except Exception:  # noqa: BLE001 - 资源渲染失败时退化为纯色控件
        pass
    _WIDGET_ASSETS = result
    return result


def _form_rules(p: dict[str, str], assets: dict[str, str]) -> str:
    """表单、分段选择器与开关的样式（放在主样式之后以便覆盖）。"""
    arrow = assets.get("chevron", "")
    switch_on = assets.get("switch_on", "")
    switch_off = assets.get("switch_off", "")
    arrow_rule = (
        f"""
QComboBox#input::down-arrow {{
    image: url("{arrow}");
    width: 13px;
    height: 13px;
}}
"""
        if arrow
        else ""
    )
    switch_rule = (
        f"""
QCheckBox::indicator:unchecked {{
    image: url("{switch_off}");
}}
QCheckBox::indicator:checked {{
    image: url("{switch_on}");
}}
"""
        if switch_off and switch_on
        else ""
    )
    return f"""
/* ---------- 滚动容器 ---------- */
#pageScroll, #pageScroll > QWidget > QWidget {{
    background: transparent;
    border: none;
}}

/* ---------- 分段选择器 ---------- */
#segmented {{
    background: rgba(0, 0, 0, 0.28);
    border: 1px solid {p["border_soft"]};
    border-radius: 11px;
}}
#segButton {{
    background: transparent;
    color: {p["subtle"]};
    border: none;
    border-radius: 8px;
    padding: 7px 20px;
    font-size: 10pt;
}}
#segButton:hover {{
    background: {p["hover"]};
    color: {p["fg"]};
}}
#segButton:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {p["accent"]}, stop:1 {p["accent2"]});
    color: #ffffff;
    font-weight: 600;
}}

/* ---------- 表单 ---------- */
#formLabel {{
    color: {p["fg"]};
    font-size: 10pt;
    font-weight: 600;
    background: transparent;
}}
#fieldHint {{
    color: {p["subtle"]};
    font-size: 8.5pt;
    background: transparent;
}}
#providerNote {{
    color: {p["subtle"]};
    font-size: 9pt;
    background: transparent;
}}
#sectionLabel {{
    color: {p["launcher"]};
    font-size: 9.5pt;
    font-weight: 600;
    background: transparent;
}}
#saveState {{
    color: {p["subtle"]};
    font-size: 9pt;
    background: transparent;
}}
QLineEdit#input, QComboBox#input, QPlainTextEdit#inputArea {{
    background: {p["entry_bg"]};
    border: 1px solid {p["border_soft"]};
    border-radius: 8px;
    padding: 7px 10px;
    color: {p["fg"]};
    selection-background-color: {p["accent"]};
}}
QLineEdit#input {{
    min-height: 19px;
}}
QLineEdit#input:hover, QComboBox#input:hover, QPlainTextEdit#inputArea:hover {{
    border: 1px solid rgba(255, 255, 255, 0.14);
}}
QLineEdit#input:focus, QComboBox#input:focus, QPlainTextEdit#inputArea:focus {{
    border: 1px solid {p["accent"]};
    background: rgba(59, 130, 246, 0.08);
}}
QLineEdit#input:disabled {{
    color: {p["subtle"]};
}}
QComboBox#input::drop-down {{
    width: 26px;
    border: none;
    background: transparent;
}}
QComboBox#input QAbstractItemView {{
    background: {p["panel_top"]};
    color: {p["fg"]};
    border: 1px solid {p["border_soft"]};
    border-radius: 8px;
    padding: 4px;
    outline: 0;
    selection-background-color: rgba(59, 130, 246, 0.30);
}}
{arrow_rule}
/* ---------- 开关 ---------- */
QCheckBox {{
    color: {p["fg"]};
    spacing: 8px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 34px;
    height: 19px;
}}
QCheckBox::indicator:disabled {{
    opacity: 140;
}}
{switch_rule}"""



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
