"""通用小部件：卡片、标题、按钮等。"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


def restyle(widget: QWidget) -> None:
    """属性变化后强制刷新 QSS（Qt 不会自动重算属性选择器）。"""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def card(*, spacing: int = 0, margins: tuple[int, int, int, int] = (16, 16, 16, 16)) -> QFrame:
    """统一样式的卡片容器。"""
    frame = QFrame()
    frame.setObjectName("card")
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


def hint(text: str, *, wrap: int | None = None, card_scoped: bool = False) -> QLabel:
    widget = QLabel(text)
    widget.setObjectName("cardHint" if card_scoped else "hint")
    widget.setWordWrap(wrap is not None)
    if wrap:
        widget.setMaximumWidth(wrap)
    return widget


def button(
    text: str,
    *,
    variant: str = "",
    on_click=None,
    minimum_width: int | None = None,
) -> QPushButton:
    widget = QPushButton(text)
    if variant:
        widget.setProperty("variant", variant)
    if on_click is not None:
        widget.clicked.connect(on_click)
    if minimum_width:
        widget.setMinimumWidth(minimum_width)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    return widget


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
    line.setStyleSheet("color: #2c2c3c; background: #2c2c3c; max-height: 1px;")
    return line
