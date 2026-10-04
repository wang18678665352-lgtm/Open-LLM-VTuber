"""通用小部件：卡片、标题、按钮、图标与阴影辅助。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..core.icons import apply_icon, pixmap
from ..core.theme import PALETTE


def restyle(widget: QWidget) -> None:
    """属性变化后强制刷新 QSS（Qt 不会自动重算属性选择器）。"""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def card(
    *,
    spacing: int = 0,
    margins: tuple[int, int, int, int] = (16, 16, 16, 16),
    object_name: str = "card",
) -> QFrame:
    """统一样式的卡片容器。"""
    frame = QFrame()
    frame.setObjectName(object_name)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return frame


def card_layout(frame: QFrame) -> QVBoxLayout:
    return frame.layout()  # type: ignore[return-value]


def label(text: str, object_name: str = "cardLabel", parent: QWidget | None = None) -> QLabel:
    widget = QLabel(text, parent)
    widget.setObjectName(object_name)
    return widget


def page_title(text: str) -> QLabel:
    widget = QLabel(text)
    widget.setObjectName("pageTitle")
    return widget


def page_header(title: str, subtitle: str = "") -> QWidget:
    """页面顶部标题 + 一行说明，统一各页面的视觉层次。"""
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(2, 0, 2, 0)
    layout.setSpacing(2)
    layout.addWidget(page_title(title))
    if subtitle:
        layout.addWidget(label(subtitle, "pageSub"))
    # 页面内容较高时不允许布局压缩标题（否则标题会被裁掉一截）；
    # 垂直方向用 Fixed，让 Qt 在 QSS 生效后按真实 sizeHint 排版。
    container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    return container


def hint(text: str, *, wrap: int | None = None, card_scoped: bool = False) -> QLabel:
    widget = QLabel(text)
    widget.setObjectName("cardHint" if card_scoped else "hint")
    widget.setWordWrap(wrap is not None)
    if wrap:
        widget.setMaximumWidth(wrap)
    return widget


def chip(text: str, object_name: str = "chip") -> QLabel:
    """小药丸标签：地址、版本号等。"""
    widget = QLabel(text)
    widget.setObjectName(object_name)
    widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return widget


def button(
    text: str,
    *,
    variant: str = "",
    on_click=None,
    minimum_width: int | None = None,
    icon_name: str | None = None,
    icon_color: str | None = None,
    icon_size: int = 18,
    tooltip: str | None = None,
) -> QPushButton:
    widget = QPushButton(text)
    if variant:
        widget.setProperty("variant", variant)
    if icon_name:
        apply_icon(
            widget,
            icon_name,
            color=icon_color or PALETTE["fg"],
            size=icon_size,
        )
    if on_click is not None:
        widget.clicked.connect(on_click)
    if minimum_width:
        widget.setMinimumWidth(minimum_width)
    if tooltip:
        widget.setToolTip(tooltip)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    return widget


def icon_button(
    name: str,
    *,
    text: str = "",
    color: str | None = None,
    size: int = 18,
    on_click=None,
    tooltip: str | None = None,
    variant: str = "ghost",
) -> QPushButton:
    """图标按钮（可带文字），用于「刷新」「清空」这类次要操作。"""
    widget = button(
        text,
        variant=variant,
        on_click=on_click,
        icon_name=name,
        icon_color=color or PALETTE["subtle"],
        icon_size=size,
        tooltip=tooltip,
    )
    return widget


def set_button_icon(
    widget: QPushButton, name: str, *, color: str | None = None, size: int = 18
) -> None:
    apply_icon(widget, name, color=color or PALETTE["fg"], size=size)


def apply_shadow(
    widget: QWidget,
    *,
    blur: int = 24,
    dy: int = 2,
    alpha: int = 38,
    color: str = "#3c4043",
) -> QGraphicsDropShadowEffect:
    """给卡片/按钮加克制的 Material 投影，增加层次感。"""
    effect = QGraphicsDropShadowEffect(widget)
    shadow_color = QColor(color)
    shadow_color.setAlpha(alpha)
    effect.setColor(shadow_color)
    effect.setBlurRadius(blur)
    effect.setOffset(0, dy)
    widget.setGraphicsEffect(effect)
    return effect


def glow(widget: QWidget, *, color: str = "#1a73e8", blur: int = 24, alpha: int = 60):
    """强调用柔和投影（用于主启动按钮），风格上不做发光。"""
    return apply_shadow(widget, blur=blur, dy=3, alpha=alpha, color=color)


def row(*widgets: QWidget, spacing: int = 10, stretch_last: bool = False) -> QWidget:
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(spacing)
    for index, widget in enumerate(widgets):
        if widget is None:
            layout.addStretch(1)
            continue
        layout.addWidget(widget)
        if stretch_last and index == len(widgets) - 1:
            layout.setStretch(index, 1)
    return container


def separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet(
        f"background: {PALETTE['border_soft']}; border: none; max-height: 1px;"
    )
    return line


def logo_pixmap(size: int = 40):
    """启动器标记（矢量绘制，任意尺寸都清晰）。"""
    from ..core.icons import logo_pixmap as _logo

    return _logo(size)


__all__ = [
    "apply_shadow",
    "button",
    "card",
    "card_layout",
    "chip",
    "glow",
    "hint",
    "icon_button",
    "label",
    "logo_pixmap",
    "page_header",
    "page_title",
    "pixmap",
    "restyle",
    "row",
    "separator",
    "set_button_icon",
]
