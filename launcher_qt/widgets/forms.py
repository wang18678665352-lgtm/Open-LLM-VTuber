"""表单控件：分段选择器、配置字段行、密码输入框。"""

from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDoubleValidator, QIntValidator
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core.icons import apply_icon
from ..core.schema import Field
from ..core.theme import PALETTE
from .common import icon_button


class SegmentedControl(QWidget):
    """分段选择器：一排放置、互斥高亮的胶囊按钮（可带图标）。"""

    changed = Signal(str)

    def __init__(
        self, items: list[tuple[str, str] | tuple[str, str, str]], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        frame = QFrame(self)
        frame.setObjectName("segmented")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(frame)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}
        self._icons: dict[str, str] = {}
        for item in items:
            key, text = item[0], item[1]
            icon_name = item[2] if len(item) > 2 else ""
            button = QPushButton(text, frame)
            button.setObjectName("segButton")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            if icon_name:
                from PySide6.QtCore import QSize

                apply_icon(button, icon_name, color=PALETTE["subtle"], size=16)
                button.setIconSize(QSize(16, 16))
                self._icons[key] = icon_name
            button.clicked.connect(lambda _checked=False, name=key: self._on_click(name))
            self._group.addButton(button)
            self._buttons[key] = button
            layout.addWidget(button)
        layout.addStretch(1)
        if items:
            self._buttons[items[0][0]].setChecked(True)
        self._refresh_icons()

    def _on_click(self, key: str) -> None:
        self._refresh_icons()
        self.changed.emit(key)

    def _refresh_icons(self) -> None:
        for key, button in self._buttons.items():
            name = self._icons.get(key)
            if not name:
                continue
            apply_icon(
                button,
                name,
                color="#ffffff" if button.isChecked() else PALETTE["subtle"],
                size=16,
            )

    def current(self) -> str:
        for key, button in self._buttons.items():
            if button.isChecked():
                return key
        return next(iter(self._buttons), "")

    def set_current(self, key: str) -> None:
        button = self._buttons.get(key)
        if button is not None:
            button.setChecked(True)
            self._refresh_icons()


class SecretEdit(QWidget):
    """密码框 + 显示/隐藏按钮。"""

    changed = Signal()

    def __init__(
        self, text: str = "", placeholder: str = "", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.edit = QLineEdit(text, self)
        self.edit.setObjectName("input")
        self.edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.edit.setPlaceholderText(placeholder)
        self.edit.textChanged.connect(lambda _text: self.changed.emit())
        self.toggle = icon_button(
            "eye",
            size=16,
            tooltip="显示 / 隐藏",
            on_click=self._toggle,
        )
        self.toggle.setCheckable(True)
        layout.addWidget(self.edit, 1)
        layout.addWidget(self.toggle)

    def _toggle(self) -> None:
        hidden = self.edit.echoMode() == QLineEdit.EchoMode.Password
        self.edit.setEchoMode(
            QLineEdit.EchoMode.Normal if hidden else QLineEdit.EchoMode.Password
        )
        apply_icon(
            self.toggle,
            "eye_off" if hidden else "eye",
            color=PALETTE["subtle"],
            size=16,
        )

    def text(self) -> str:
        return self.edit.text().strip()

    def setText(self, value: str) -> None:
        self.edit.setText(value or "")

    def setPlaceholderText(self, value: str) -> None:
        self.edit.setPlaceholderText(value or "")


class FormField(QWidget):
    """根据 schema 生成的一个可编辑字段。"""

    changed = Signal()

    def __init__(self, spec: Field, value: Any = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.spec = spec
        self.editor: QWidget | None = None
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        initial = value if value is not None else spec.default
        self.initial = initial
        kind = spec.kind

        if kind == "bool":
            box = QCheckBox(self)
            box.setObjectName("switchBox")
            box.setCursor(Qt.CursorShape.PointingHandCursor)
            box.setChecked(bool(initial))
            box.stateChanged.connect(lambda _state: self.changed.emit())
            self.editor = box
        elif kind == "choice":
            combo = QComboBox(self)
            combo.setObjectName("input")
            combo.setEditable(True)
            combo.setCursor(Qt.CursorShape.PointingHandCursor)
            combo.addItems(list(spec.choices))
            text = "" if initial is None else str(initial)
            if text:
                combo.setCurrentText(text)
            elif spec.choices:
                combo.setCurrentText(spec.choices[0])
            combo.currentTextChanged.connect(lambda _text: self.changed.emit())
            self.editor = combo
        elif kind == "secret":
            secret = SecretEdit("" if initial is None else str(initial), spec.placeholder, self)
            secret.changed.connect(lambda: self.changed.emit())
            self.editor = secret
        elif kind == "multiline":
            view = QPlainTextEdit(self)
            view.setObjectName("inputArea")
            view.setPlainText("" if initial is None else str(initial))
            view.setFixedHeight(84)
            view.textChanged.connect(lambda: self.changed.emit())
            self.editor = view
        elif kind == "path":
            holder = QWidget(self)
            holder_layout = QHBoxLayout(holder)
            holder_layout.setContentsMargins(0, 0, 0, 0)
            holder_layout.setSpacing(6)
            edit = QLineEdit(holder)
            edit.setObjectName("input")
            edit.setPlaceholderText(spec.placeholder or "选择一个文件或目录")
            edit.setText("" if initial is None else str(initial))
            edit.textChanged.connect(lambda _text: self.changed.emit())
            browse = icon_button("folder", size=16, tooltip="浏览…", on_click=self._browse)
            holder_layout.addWidget(edit, 1)
            holder_layout.addWidget(browse)
            self.path_edit = edit
            self.editor = holder
        else:  # text / int / float / json
            edit = QLineEdit(self)
            edit.setObjectName("input")
            edit.setPlaceholderText(spec.placeholder)
            if kind == "int":
                edit.setValidator(QIntValidator(-100000000, 100000000, self))
            elif kind == "float":
                validator = QDoubleValidator(-100000.0, 100000.0, 4, self)
                validator.setNotation(QDoubleValidator.Notation.StandardNotation)
                edit.setValidator(validator)
            if initial is not None:
                edit.setText(str(initial))
            edit.textChanged.connect(lambda _text: self.changed.emit())
            self.editor = edit

        layout.addWidget(self.editor, 1)

    # ------------------------------------------------------------------
    def _browse(self) -> None:
        current = self.path_edit.text()
        chosen, _filter = QFileDialog.getOpenFileName(self, "选择文件", current)
        if not chosen:
            chosen = QFileDialog.getExistingDirectory(self, "选择目录", current)
        if chosen:
            self.path_edit.setText(chosen)

    def set_value(self, value: Any) -> None:
        editor = self.editor
        if isinstance(editor, QCheckBox):
            editor.setChecked(bool(value))
        elif isinstance(editor, QComboBox):
            editor.setCurrentText("" if value is None else str(value))
        elif isinstance(editor, SecretEdit):
            editor.setText("" if value is None else str(value))
        elif isinstance(editor, QPlainTextEdit):
            editor.setPlainText("" if value is None else str(value))
        elif hasattr(self, "path_edit"):
            self.path_edit.setText("" if value is None else str(value))
        elif isinstance(editor, QLineEdit):
            editor.setText("" if value is None else str(value))

    def _blank(self) -> Any:
        """输入框为空时的取值：原本就是 null 的字段保持 null，不要写成空字符串。"""
        return None if self.initial is None else ""

    def value(self) -> Any:
        """读取当前值；格式非法时抛出 ValueError。"""
        spec = self.spec
        editor = self.editor
        if isinstance(editor, QCheckBox):
            return editor.isChecked()
        if isinstance(editor, QComboBox):
            text = editor.currentText().strip()
            return text or None
        if isinstance(editor, SecretEdit):
            text = editor.text()
            return text if text else self._blank()
        if isinstance(editor, QPlainTextEdit):
            text = editor.toPlainText().strip()
            return text if text else self._blank()
        if hasattr(self, "path_edit"):
            return self.path_edit.text().strip() or self._blank()
        if isinstance(editor, QLineEdit):
            text = editor.text().strip()
            if spec.kind == "int":
                if not text:
                    return None
                try:
                    return int(float(text))
                except ValueError as exc:
                    raise ValueError(f"「{spec.label}」需要填写整数") from exc
            if spec.kind == "float":
                if not text:
                    return None
                try:
                    return float(text)
                except ValueError as exc:
                    raise ValueError(f"「{spec.label}」需要填写数字") from exc
            if spec.kind == "json":
                if not text:
                    return self._blank()
                try:
                    return json.loads(text)
                except ValueError as exc:
                    raise ValueError(
                        f"「{spec.label}」需要填写合法的 JSON，例如 " + '{"effort": "low"}'
                    ) from exc
            return text if text else self._blank()
        return None


def field_rows(
    fields: tuple[Field, ...],
    values: dict[str, Any],
    *,
    label_width: int = 176,
) -> tuple[QWidget, dict[str, FormField]]:
    """把一组字段排成「标签 + 输入框 + 说明」的表单。"""
    container = QWidget()
    grid = QGridLayout(container)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setHorizontalSpacing(14)
    grid.setVerticalSpacing(12)
    grid.setColumnStretch(1, 1)

    widgets: dict[str, FormField] = {}
    for row, spec in enumerate(fields):
        caption = QLabel(spec.label)
        caption.setObjectName("formLabel")
        caption.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        caption.setWordWrap(True)

        # 标签略微下移，使其视觉中心与右侧输入框对齐（而不是与整行对齐）
        caption_holder = QWidget()
        caption_layout = QVBoxLayout(caption_holder)
        caption_layout.setContentsMargins(0, 7, 0, 0)
        caption_layout.setSpacing(0)
        caption_layout.addWidget(caption)
        caption_layout.addStretch(1)
        caption_holder.setFixedWidth(label_width)

        holder = QWidget()
        holder_layout = QVBoxLayout(holder)
        holder_layout.setContentsMargins(0, 0, 0, 0)
        holder_layout.setSpacing(3)

        editor = FormField(spec, values.get(spec.key), holder)
        holder_layout.addWidget(editor)
        if spec.hint:
            note = QLabel(spec.hint)
            note.setObjectName("fieldHint")
            note.setWordWrap(True)
            holder_layout.addWidget(note)

        grid.addWidget(caption_holder, row, 0)
        grid.addWidget(holder, row, 1)
        widgets[spec.key] = editor
    return container, widgets


__all__ = ["FormField", "SecretEdit", "SegmentedControl", "field_rows"]
