"""简约 Google / Material 风格主题：调色板、全局 QSS 与 Windows 原生窗口装饰。

配色参考 Google Material 浅色主题：白色表面、#f8f9fa 背景、
#1a73e8 主色、#5f6368 次要文字、#dadce0 描边，圆角与阴影都很克制。
"""

from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase

IS_WIN = sys.platform.startswith("win")

PALETTE: dict[str, str] = {
    # 表面
    "bg": "#f8f9fa",
    "window_top": "#ffffff",
    "window_bottom": "#f8f9fa",
    "sidebar": "#ffffff",
    "sidebar_top": "#ffffff",
    "panel": "#ffffff",
    "panel_top": "#ffffff",
    "panel_bottom": "#ffffff",
    "panel_alt": "#f1f3f4",
    # 文字
    "fg": "#202124",
    "subtle": "#5f6368",
    "muted": "#80868b",
    # 主色
    "accent": "#1a73e8",
    "accent_hover": "#1765cc",
    "accent_press": "#185abc",
    "accent2": "#4285f4",
    "accent_container": "#e8f0fe",
    "accent_on_container": "#1967d2",
    # 语义色
    "danger": "#d93025",
    "danger_hover": "#c5221f",
    "ok": "#1e8e3e",
    "warn": "#e37400",
    "err": "#d93025",
    "info": "#1a73e8",
    "debug": "#80868b",
    # 控制台与输入
    "console_bg": "#f1f3f4",
    "console_fg": "#3c4043",
    "entry_bg": "#ffffff",
    "border": "#dadce0",
    "border_soft": "#e8eaed",
    "tray_border": "#dadce0",
    "launcher": "#1967d2",
    "hero_a": "#ffffff",
    "hero_b": "#ffffff",
    "hover": "#f1f3f4",
    "hover_strong": "#e8eaed",
    "shadow": "rgba(60, 64, 67, 0.20)",
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
    """界面主字体：Segoe UI 最接近 Google 的 Roboto，中文由系统字体回退。"""
    return pick_font(
        ("Segoe UI Variable Text", "Segoe UI", "Roboto", "Microsoft YaHei UI"),
        QFont().defaultFamily(),
    )


def ui_font_stack() -> str:
    """QSS 用的字体列表：西文走 Segoe UI/Roboto，中文回退到雅黑。"""
    return '"Segoe UI Variable Text", "Segoe UI", Roboto, "Microsoft YaHei UI", "Microsoft YaHei"'


def mono_font_family() -> str:
    return pick_font(
        ("Cascadia Mono", "Consolas", "JetBrains Mono", "Courier New"), "Courier New"
    )


def build_stylesheet() -> str:
    p = PALETTE
    ui = ui_font_stack()
    mono = mono_font_family()
    assets = _widget_assets()
    return f"""
* {{
    outline: 0;
}}
QWidget {{
    background: transparent;
    color: {p["fg"]};
    font-family: {ui};
    font-size: 10pt;
}}
QLabel {{
    background: transparent;
}}
QMainWindow, QDialog {{
    background: {p["bg"]};
}}
QToolTip {{
    background: {p["console_fg"]};
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 6px 9px;
}}

/* ---------- 内容区背景 ---------- */
#content {{
    background: {p["bg"]};
}}

/* ---------- 侧边栏 ---------- */
#sidebar {{
    background: {p["sidebar"]};
    border-right: 1px solid {p["border_soft"]};
}}
#sidebarTitle {{
    color: {p["fg"]};
    font-size: 12pt;
    font-weight: 600;
    background: transparent;
}}
#sidebarSub {{
    color: {p["muted"]};
    font-size: 8.5pt;
    background: transparent;
}}
#navButton {{
    background: transparent;
    color: {p["subtle"]};
    border: none;
    border-radius: 8px;
    padding: 9px 12px;
    text-align: left;
    font-size: 10pt;
}}
#navButton:hover {{
    background: {p["hover"]};
    color: {p["fg"]};
}}
#navButton:checked {{
    background: {p["accent_container"]};
    color: {p["accent_on_container"]};
    font-weight: 600;
}}
#statusChip {{
    background: {p["hover"]};
    border: none;
    border-radius: 8px;
}}
#statusDot {{
    background: {p["muted"]};
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
    background: {p["panel"]};
    border: 1px solid {p["border_soft"]};
    border-radius: 12px;
}}
#hero {{
    background: #f8fbff;
    border: 1px solid #d2e3fc;
    border-radius: 12px;
}}
#pageTitle {{
    color: {p["fg"]};
    font-size: 17pt;
    font-weight: 500;
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
    color: {p["fg"]};
    font-size: 15pt;
    font-weight: 600;
    background: transparent;
}}
#chip {{
    background: {p["hover"]};
    border: none;
    border-radius: 6px;
    color: {p["console_fg"]};
    font-family: "{mono}";
    font-size: 9.5pt;
    padding: 4px 9px;
}}
#pill {{
    background: {p["accent_container"]};
    border: none;
    border-radius: 9px;
    color: {p["accent_on_container"]};
    font-size: 9pt;
    padding: 3px 10px;
}}

/* ---------- 按钮 ---------- */
QPushButton {{
    background: {p["panel"]};
    color: {p["accent"]};
    border: 1px solid {p["border"]};
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 500;
}}
QPushButton:hover {{
    background: #f6faff;
    border-color: #c3d5f5;
}}
QPushButton:pressed {{
    background: {p["accent_container"]};
}}
QPushButton:disabled {{
    background: {p["panel"]};
    color: #bdc1c6;
    border-color: {p["border_soft"]};
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
    background: {p["accent"]};
    color: #ffffff;
    border: 1px solid transparent;
    font-weight: 500;
    padding: 8px 16px;
}}
QPushButton[variant="accent"]:hover {{
    background: {p["accent_hover"]};
}}
QPushButton[variant="accent"]:pressed {{
    background: {p["accent_press"]};
}}
QPushButton[variant="launch"] {{
    background: {p["accent"]};
    color: #ffffff;
    border: 1px solid transparent;
    border-radius: 10px;
    font-size: 15pt;
    font-weight: 600;
    padding: 22px 30px;
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
    border: 1px solid transparent;
    border-radius: 10px;
    font-size: 15pt;
    font-weight: 600;
    padding: 22px 30px;
}}
QPushButton[variant="launchStop"]:hover {{
    background: {p["danger_hover"]};
}}
QPushButton[variant="launchStop"]:pressed {{
    background: #a50e0e;
}}

/* ---------- 输入控件 ---------- */
QLineEdit {{
    background: {p["entry_bg"]};
    color: {p["fg"]};
    border: 1px solid {p["border"]};
    border-radius: 6px;
    padding: 7px 10px;
    selection-background-color: {p["accent_container"]};
    selection-color: {p["fg"]};
}}
QLineEdit:hover {{
    border-color: #bdc1c6;
}}
QLineEdit:focus {{
    border: 1px solid {p["accent"]};
}}
QCheckBox {{
    background: transparent;
    color: {p["fg"]};
    spacing: 8px;
}}
QCheckBox:hover {{
    color: {p["accent"]};
}}
QCheckBox:disabled {{
    color: {p["muted"]};
}}

/* ---------- 控制台 / 环境信息 ---------- */
#console {{
    background: {p["console_bg"]};
    color: {p["console_fg"]};
    border: none;
    border-radius: 8px;
    padding: 10px 12px;
    font-family: "{mono}";
    font-size: 9.5pt;
    selection-background-color: {p["accent_container"]};
    selection-color: {p["fg"]};
}}
#envInfo {{
    background: {p["console_bg"]};
    color: {p["console_fg"]};
    border: none;
    border-radius: 8px;
    padding: 10px 12px;
    font-family: "{mono}";
    font-size: 9.5pt;
}}

/* ---------- 表格 ---------- */
QTreeWidget {{
    background: {p["panel"]};
    alternate-background-color: #fafbfc;
    color: {p["fg"]};
    border: 1px solid {p["border_soft"]};
    border-radius: 8px;
    padding: 2px;
}}
QTreeWidget::item {{
    padding: 8px 4px;
    border: none;
}}
QTreeWidget::item:selected {{
    background: {p["accent_container"]};
    color: {p["fg"]};
}}
QHeaderView::section {{
    background: transparent;
    color: {p["subtle"]};
    border: none;
    border-bottom: 1px solid {p["border_soft"]};
    padding: 8px 6px;
    font-weight: 600;
}}

/* ---------- 滚动条 ---------- */
QScrollBar:vertical {{
    background: transparent;
    width: 11px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #dadce0;
    border-radius: 5px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #bdc1c6;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 11px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: #dadce0;
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
    background: {p["panel"]};
    color: {p["fg"]};
    border: 1px solid {p["border_soft"]};
    border-radius: 8px;
    padding: 6px;
}}
QMenu::item {{
    padding: 7px 20px;
    border-radius: 6px;
}}
QMenu::item:selected {{
    background: {p["hover"]};
    color: {p["fg"]};
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
    又不需要往仓库里塞二进制资源。按 3 倍分辨率渲染，缩放后依然锐利。
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

        # Material 3 开关：开（蓝底白钮）/ 关（灰底白钮）
        for state in (False, True):
            scale = 3
            width, height = 34 * scale, 19 * scale
            pixmap = QPixmap(width, height)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(PALETTE["accent"] if state else "#dadce0"))
            radius = (height - 2 * scale) / 2
            painter.drawRoundedRect(
                QRectF(scale, scale, width - 2 * scale, height - 2 * scale), radius, radius
            )
            knob = height - 8 * scale
            left = (width - 4 * scale - knob) if state else 4 * scale
            painter.setBrush(QColor("#ffffff"))
            painter.drawEllipse(QRectF(left, 4 * scale, knob, knob))
            painter.end()
            save(f"switch_{'on' if state else 'off'}.png", pixmap)

        # 下拉箭头
        scale = 4
        size = 24 * scale
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        pen = QPen(QColor(PALETTE["subtle"]))
        pen.setWidthF(2.0 * scale)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        path = QPainterPath()
        path.moveTo(7.6 * scale, 10.2 * scale)
        path.lineTo(12.0 * scale, 14.6 * scale)
        path.lineTo(16.4 * scale, 10.2 * scale)
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
    width: 12px;
    height: 12px;
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

/* ---------- 分段选择器（Google 分段按钮） ---------- */
#segmented {{
    background: {p["hover"]};
    border: none;
    border-radius: 8px;
}}
#segButton {{
    background: transparent;
    color: {p["subtle"]};
    border: none;
    border-radius: 7px;
    padding: 7px 20px;
    font-size: 10pt;
    font-weight: 500;
}}
#segButton:hover {{
    color: {p["fg"]};
}}
#segButton:checked {{
    background: {p["panel"]};
    color: {p["accent"]};
    font-weight: 600;
}}

/* ---------- 表单 ---------- */
#formLabel {{
    color: {p["fg"]};
    font-size: 10pt;
    font-weight: 500;
    background: transparent;
}}
#fieldHint {{
    color: {p["muted"]};
    font-size: 8.5pt;
    background: transparent;
}}
#providerNote {{
    color: {p["subtle"]};
    font-size: 9pt;
    background: transparent;
}}
#sectionLabel {{
    color: {p["accent"]};
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
    border: 1px solid {p["border"]};
    border-radius: 6px;
    padding: 7px 10px;
    color: {p["fg"]};
    selection-background-color: {p["accent_container"]};
    selection-color: {p["fg"]};
}}
QLineEdit#input {{
    min-height: 19px;
}}
QLineEdit#input:hover, QComboBox#input:hover, QPlainTextEdit#inputArea:hover {{
    border: 1px solid #bdc1c6;
}}
QLineEdit#input:focus, QComboBox#input:focus, QPlainTextEdit#inputArea:focus {{
    border: 1px solid {p["accent"]};
}}
QLineEdit#input:disabled {{
    color: {p["muted"]};
    background: {p["hover"]};
}}
QComboBox#input::drop-down {{
    width: 26px;
    border: none;
    background: transparent;
}}
QComboBox#input QAbstractItemView {{
    background: {p["panel"]};
    color: {p["fg"]};
    border: 1px solid {p["border_soft"]};
    border-radius: 8px;
    padding: 4px;
    outline: 0;
    selection-background-color: {p["hover"]};
    selection-color: {p["fg"]};
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
# Windows 原生窗口装饰：浅色标题栏 + Win11 圆角
# ---------------------------------------------------------------------------

_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWCP_ROUND = 2


def apply_native_chrome(widget, dark: bool = False) -> None:
    """让 Win10/11 的原生标题栏跟随主题（默认浅色），并启用 Win11 圆角。

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
