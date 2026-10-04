"""页面：一键启动。"""

from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QVBoxLayout, QWidget

from ..core.config import server_url
from ..widgets.common import (
    button,
    card,
    card_layout,
    hint,
    label,
    page_title,
    restyle,
)
from ..widgets.console import ConsoleView

OPTIONS = (
    ("verbose", "详细日志 (--verbose)"),
    ("hf_mirror", "HF 镜像加速 (--hf_mirror)"),
    ("open_browser", "启动后自动打开浏览器"),
)


class HomePage(QWidget):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        layout.addWidget(page_title("一键启动"))

        # ---- 启动卡片 ----
        launch_card = card(margins=(18, 18, 18, 18))
        launch_layout = card_layout(launch_card)
        launch_layout.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(18)
        self.launch_button = button(
            "一 键 启 动", variant="launch", on_click=window.toggle_server
        )
        self.launch_button.setMinimumWidth(240)
        top.addWidget(self.launch_button)

        state_box = QVBoxLayout()
        state_box.setSpacing(6)
        self.state_label = label("状态：未运行", "bigState")
        self.addr_label = label(f"地址：{server_url()}", "cardHint")
        state_box.addWidget(self.state_label)
        state_box.addWidget(self.addr_label)
        state_box.addStretch(1)
        top.addLayout(state_box, 1)

        self.open_button = button(
            "打开网页", on_click=lambda: webbrowser.open(server_url())
        )
        top.addWidget(self.open_button, 0, Qt.AlignmentFlag.AlignTop)
        launch_layout.addLayout(top)

        options_row = QHBoxLayout()
        options_row.setSpacing(18)
        self.option_boxes: dict[str, QCheckBox] = {}
        for key, text in OPTIONS:
            box = QCheckBox(text)
            box.setChecked(bool(window.options.get(key, False)))
            box.toggled.connect(
                lambda checked, name=key: self.window.set_option(name, checked)
            )
            self.option_boxes[key] = box
            options_row.addWidget(box)
        options_row.addStretch(1)
        launch_layout.addLayout(options_row)
        layout.addWidget(launch_card)

        # ---- 控制台卡片 ----
        console_card = card(margins=(14, 12, 14, 14))
        console_layout = card_layout(console_card)
        console_layout.setSpacing(8)

        toolbar = QHBoxLayout()
        toolbar.addWidget(label("控制台输出", "cardTitle"))
        toolbar.addStretch(1)
        self.autoscroll_box = QCheckBox("自动滚动")
        self.autoscroll_box.setChecked(bool(window.options.get("autoscroll", True)))
        self.autoscroll_box.toggled.connect(
            lambda checked: self.window.set_option("autoscroll", checked)
        )
        toolbar.addWidget(self.autoscroll_box)
        toolbar.addWidget(button("清空", on_click=self.clear_console))
        console_layout.addLayout(toolbar)

        self.console = ConsoleView()
        console_layout.addWidget(self.console, 1)
        layout.addWidget(console_card, 1)

        tip = hint(
            "提示：首次使用建议先在「疑难解答」页一键扫描，确认依赖与模型就绪。"
        )
        layout.addWidget(tip)

    # ------------------------------------------------------------------
    def clear_console(self) -> None:
        self.console.clear_all()

    def log(self, text: str) -> None:
        self.console.append_text(text, autoscroll=self.autoscroll_box.isChecked())

    def set_running(self, running: bool) -> None:
        if running:
            self.launch_button.setText("终 止 运 行")
            self.launch_button.setProperty("variant", "launchStop")
            self.state_label.setText("状态：运行中")
        else:
            self.launch_button.setText("一 键 启 动")
            self.launch_button.setProperty("variant", "launch")
            self.state_label.setText("状态：未运行")
        restyle(self.launch_button)
        for box in self.option_boxes.values():
            box.setEnabled(not running)

    def refresh_addr(self) -> None:
        self.addr_label.setText(f"地址：{server_url()}")

    def on_show(self) -> None:
        self.refresh_addr()
