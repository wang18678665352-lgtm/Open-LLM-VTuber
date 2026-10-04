"""模型配置页：在启动器里直接编辑 API Key / 接口地址 / 语音引擎。"""

from __future__ import annotations

import threading
import time
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..core.config import CONF_PATH, conf_get_dict, conf_get_path, conf_set
from ..core.netcheck import check_file, check_url
from ..core.schema import SECTIONS, Provider, section
from ..core.system import open_path
from ..core.theme import PALETTE
from ..widgets.common import (
    button,
    card,
    card_layout,
    chip,
    hint,
    icon_button,
    page_header,
    separator,
)
from ..widgets.forms import FormField, SegmentedControl, field_rows


class ModelsPage(QWidget):
    """分三段（对话模型 / 语音合成 / 语音识别）配置 conf.yaml。"""

    probeFinished = Signal(bool, str)

    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self.section_key = SECTIONS[0].key
        self.provider_key = ""
        self.fields: dict[str, FormField] = {}
        self._form_widget: QWidget | None = None
        self.dirty = False
        self.probeFinished.connect(self._on_probe_finished)
        self._build()
        QShortcut(QKeySequence.StandardKey.Save, self, activated=self.save)
        QShortcut(QKeySequence.StandardKey.Refresh, self, activated=self.reload)
        self.reload()

    # ------------------------------------------------------------------
    # 界面
    # ------------------------------------------------------------------
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 18, 22, 16)
        root.setSpacing(14)
        root.addWidget(
            page_header(
                "模型配置",
                "在这里填写 API Key、接口地址与语音引擎，保存后写入 conf.yaml",
            )
        )

        top = QHBoxLayout()
        top.setSpacing(10)
        self.segmented = SegmentedControl(
            [(item.key, item.title, item.icon) for item in SECTIONS]
        )
        self.segmented.changed.connect(self.switch_section)
        top.addWidget(self.segmented, 1)
        top.addWidget(
            icon_button(
                "refresh",
                text="重新读取",
                size=16,
                tooltip="从 conf.yaml 重新读取当前引擎的参数（放弃未保存的修改）",
                on_click=self.reload,
            )
        )
        top.addWidget(
            icon_button(
                "file",
                text="打开 conf.yaml",
                size=16,
                tooltip=str(CONF_PATH),
                on_click=self.open_conf,
            )
        )
        root.addLayout(top)

        scroll = QScrollArea()
        scroll.setObjectName("pageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 8, 0)
        body_layout.setSpacing(14)

        # ---- 引擎选择 ----
        engine_card = card(spacing=10)
        engine_layout = card_layout(engine_card)

        engine_row = QHBoxLayout()
        engine_row.setSpacing(10)
        engine_caption = QLabel("当前引擎")
        engine_caption.setObjectName("sectionLabel")
        engine_caption.setFixedWidth(84)
        self.engine_combo = QComboBox()
        self.engine_combo.setObjectName("input")
        self.engine_combo.setMinimumWidth(300)
        self.engine_combo.currentIndexChanged.connect(self._on_engine_changed)
        self.test_button = button(
            "测试连接",
            variant="accent",
            icon_name="sparkle",
            icon_color="#ffffff",
            icon_size=16,
            on_click=self.test_connection,
        )
        engine_row.addWidget(engine_caption)
        engine_row.addWidget(self.engine_combo, 1)
        engine_row.addWidget(self.test_button)
        engine_layout.addLayout(engine_row)

        self.note_label = QLabel()
        self.note_label.setObjectName("providerNote")
        self.note_label.setWordWrap(True)
        self.note_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        engine_layout.addWidget(self.note_label)

        info_row = QHBoxLayout()
        info_row.setSpacing(8)
        self.path_chip = chip("")
        self.result_label = QLabel("")
        self.result_label.setObjectName("saveState")
        self.result_label.setWordWrap(True)
        info_row.addWidget(self.path_chip)
        info_row.addWidget(self.result_label, 1)
        engine_layout.addLayout(info_row)
        body_layout.addWidget(engine_card)

        # ---- 参数表单 ----
        self.form_card = card(spacing=12)
        form_layout = card_layout(self.form_card)
        form_title = QHBoxLayout()
        form_caption = QLabel("参数")
        form_caption.setObjectName("sectionLabel")
        form_title.addWidget(form_caption)
        form_title.addStretch(1)
        self.form_hint = QLabel("")
        self.form_hint.setObjectName("saveState")
        form_title.addWidget(self.form_hint)
        form_layout.addLayout(form_title)
        self.form_host = QWidget()
        self.form_host_layout = QVBoxLayout(self.form_host)
        self.form_host_layout.setContentsMargins(0, 0, 0, 0)
        self.form_host_layout.setSpacing(0)
        form_layout.addWidget(self.form_host)
        body_layout.addWidget(self.form_card)
        body_layout.addStretch(1)

        scroll.setWidget(body)
        self.scroll = scroll
        root.addWidget(scroll, 1)

        # ---- 底部保存栏 ----
        root.addWidget(separator())
        footer = QHBoxLayout()
        footer.setSpacing(12)
        self.save_button = button(
            "保存配置",
            variant="accent",
            icon_name="save",
            icon_color="#ffffff",
            icon_size=16,
            on_click=self.save,
        )
        self.save_button.setMinimumWidth(132)
        footer.addWidget(self.save_button)
        self.save_state = QLabel("配置只写入 conf.yaml，不会修改项目源码。")
        self.save_state.setObjectName("saveState")
        footer.addWidget(self.save_state, 1)
        footer.addWidget(
            hint("保存前会自动备份为 conf.yaml.launcher.bak；重启服务后生效。")
        )
        root.addLayout(footer)

    # ------------------------------------------------------------------
    # 数据加载
    # ------------------------------------------------------------------
    def switch_section(self, key: str) -> None:
        self.section_key = key
        self.reload()

    def reload(self) -> None:
        """从 conf.yaml 重新读取当前分段与引擎。"""
        current_section = section(self.section_key)
        if current_section is None:
            return
        selected = str(
            conf_get_path(current_section.selector_path) or current_section.providers[0].key
        )
        provider = current_section.provider(selected) or current_section.providers[0]
        self.provider_key = provider.key

        self.engine_combo.blockSignals(True)
        self.engine_combo.clear()
        for item in current_section.providers:
            self.engine_combo.addItem(f"{item.name}（{item.key}）", item.key)
        index = self.engine_combo.findData(provider.key)
        self.engine_combo.setCurrentIndex(max(index, 0))
        self.engine_combo.blockSignals(False)
        self.segmented.set_current(self.section_key)

        self._load_provider(provider)
        self._set_dirty(False)
        self.result_label.setText("")

    def _load_provider(self, provider: Provider) -> None:
        current_section = section(self.section_key)
        if current_section is None:
            return
        base = f"{current_section.base_path}.{provider.key}"
        values = conf_get_dict(base)
        self.note_label.setText(provider.note or "")
        self.note_label.setVisible(bool(provider.note))
        self.path_chip.setText(base)
        self.path_chip.setToolTip(f"conf.yaml 中的位置：{base}")

        if self._form_widget is not None:
            # 先脱离父级再 deleteLater：否则旧控件会残留一帧（并叠在新表单上）
            self.form_host_layout.removeWidget(self._form_widget)
            self._form_widget.hide()
            self._form_widget.setParent(None)
            self._form_widget.deleteLater()
            self._form_widget = None
        self.fields = {}

        if provider.fields:
            widget, fields = field_rows(provider.fields, values)
            for item in fields.values():
                item.changed.connect(self._on_field_changed)
            self.fields = fields
            self._form_widget = widget
            self.form_hint.setText(f"{len(provider.fields)} 个可编辑项")
        else:
            empty = QLabel("该引擎无需额外配置，选择后保存即可。")
            empty.setObjectName("providerNote")
            self._form_widget = empty
            self.form_hint.setText("无需配置")
        self.form_host_layout.addWidget(self._form_widget)

        # LLM 分段额外提示当前 agent 类型
        if current_section.key == "llm":
            agent = conf_get_path(
                "character_config.agent_config.conversation_agent_choice", "basic_memory_agent"
            )
            self.form_hint.setText(f"{len(provider.fields)} 个可编辑项 · 会话代理：{agent}")

    def _on_engine_changed(self, _index: int) -> None:
        key = self.engine_combo.currentData()
        current_section = section(self.section_key)
        if not key or current_section is None or key == self.provider_key:
            return
        provider = current_section.provider(str(key))
        if provider is None:
            return
        self.provider_key = provider.key
        self._load_provider(provider)
        self._set_dirty(True)

    def _on_field_changed(self) -> None:
        self._set_dirty(True)

    def _set_dirty(self, dirty: bool) -> None:
        self.dirty = dirty
        if dirty:
            self.save_state.setText("有未保存的修改，点击「保存配置」写入 conf.yaml。")
            self.save_state.setStyleSheet(f"color: {PALETTE['warn']};")
        else:
            self.save_state.setText("配置只写入 conf.yaml，不会修改项目源码。")
            self.save_state.setStyleSheet("")

    def _current_values(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for key, widget in self.fields.items():
            try:
                values[key] = widget.value()
            except ValueError:
                values[key] = None
        return values

    # ------------------------------------------------------------------
    # 操作
    # ------------------------------------------------------------------
    def save(self) -> None:
        current_section = section(self.section_key)
        provider = current_section.provider(self.provider_key) if current_section else None
        if current_section is None or provider is None:
            return
        updates: dict[str, Any] = {current_section.selector_path: provider.key}
        for key, widget in self.fields.items():
            try:
                updates[f"{current_section.base_path}.{provider.key}.{key}"] = widget.value()
            except ValueError as exc:
                QMessageBox.warning(self, "无法保存", str(exc))
                return
        ok, message = conf_set(updates)
        if ok:
            self._set_dirty(False)
            self.save_state.setText(f"已保存到 conf.yaml · {time.strftime('%H:%M:%S')}")
            self.save_state.setStyleSheet(f"color: {PALETTE['ok']};")
            self.result_label.setText("已保存，重启服务后生效。")
        else:
            QMessageBox.critical(self, "保存失败", message)

    def test_connection(self) -> None:
        current_section = section(self.section_key)
        provider = current_section.provider(self.provider_key) if current_section else None
        if provider is None:
            return
        values = self._current_values()
        self.test_button.setEnabled(False)
        self.result_label.setText("正在测试连接…")
        self.result_label.setStyleSheet(f"color: {PALETTE['subtle']};")
        threading.Thread(
            target=self._probe_worker, args=(provider, values), daemon=True
        ).start()

    def _probe_worker(self, provider: Provider, values: dict[str, Any]) -> None:
        try:
            if provider.url_field:
                url = str(values.get(provider.url_field) or "")
                if not url:
                    ok, message = False, f"请先填写「{provider.url_field}」"
                else:
                    ok, message = check_url(url)
            elif provider.path_field:
                path = str(values.get(provider.path_field) or "")
                ok, message = check_file(path)
            elif provider.secret_field:
                secret = str(values.get(provider.secret_field) or "")
                if secret:
                    ok, message = True, f"已填写 API Key（{len(secret)} 个字符）；启动器不会发起付费请求，请启动服务后验证。"
                else:
                    ok, message = False, "尚未填写 API Key"
            else:
                ok, message = True, "该引擎使用本地组件，无需网络连接测试。"
        except Exception as exc:  # noqa: BLE001
            ok, message = False, f"检查失败：{exc}"
        self.probeFinished.emit(ok, message)

    def _on_probe_finished(self, ok: bool, message: str) -> None:
        self.test_button.setEnabled(True)
        self.result_label.setText(("✓ " if ok else "✗ ") + message)
        self.result_label.setStyleSheet(
            f"color: {PALETTE['ok'] if ok else PALETTE['err']};"
        )

    def open_conf(self) -> None:
        open_path(CONF_PATH)

    def on_show(self) -> None:
        self.reload()

    def screenshot_variants(self) -> list[tuple[str, object]]:
        """供 ``--screenshot`` 使用：为每个分段（以及表单底部）各生成一张截图。"""
        from PySide6.QtWidgets import QApplication

        def select(key: str, bottom: bool = False):
            def run() -> None:
                self.segmented.set_current(key)
                self.switch_section(key)
                QApplication.processEvents()
                bar = self.scroll.verticalScrollBar()
                bar.setValue(bar.maximum() if bottom else 0)

            return run

        variants: list[tuple[str, object]] = []
        for index, item in enumerate(SECTIONS):
            variants.append((item.key, select(item.key)))
            if index:
                variants.append((f"{item.key}-bottom", select(item.key, bottom=True)))
        return variants


__all__ = ["ModelsPage"]
