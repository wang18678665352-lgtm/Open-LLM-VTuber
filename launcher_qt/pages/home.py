"""页面：一键启动。"""

from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..core.config import server_url
from ..core.icons import apply_icon, pixmap
from ..core.theme import PALETTE
from ..widgets.common import (
    apply_shadow,
    button,
    card,
    card_layout,
    chip,
    glow,
    hint,
    icon_button,
    label,
    page_header,
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
        layout.setContentsMargins(22, 18, 22, 16)
        layout.setSpacing(14)
        layout.addWidget(
            page_header("一键启动", "启动或停止本地服务，并实时查看运行日志")
        )

        # ---- 启动卡片（渐变主视觉）----
        hero = card(margins=(22, 20, 22, 18), object_name="hero")
        hero_layout = card_layout(hero)
        hero_layout.setSpacing(16)
        apply_shadow(hero, blur=40, dy=14, alpha=110, color="#05070f")

        top = QHBoxLayout()
        top.setSpacing(20)

        self.launch_button = button(
            "一 键 启 动", variant="launch", on_click=window.toggle_server
        )
        self.launch_button.setMinimumWidth(248)
        apply_icon(self.launch_button, "play", color="#ffffff", size=26)
        self._launch_glow = glow(self.launch_button, color="#4f8cf7", blur=44, alpha=150)
        top.addWidget(self.launch_button)

        state_box = QVBoxLayout()
        state_box.setSpacing(4)
        state_box.addWidget(label("服务状态", "cardHint"))

        state_row = QHBoxLayout()
        state_row.setSpacing(8)
        self.state_dot = QLabel()
        self.state_dot.setFixedSize(9, 9)
        self._paint_state_dot(False)
        self.state_label = label("未运行", "bigState")
        state_row.addWidget(self.state_dot, 0, Qt.AlignmentFlag.AlignVCenter)
        state_row.addWidget(self.state_label)
        state_row.addStretch(1)
        state_box.addLayout(state_row)

        self.addr_label = chip(server_url())
        self.addr_label.setToolTip("服务地址（可在「高级选项」中修改监听地址与端口）")
        addr_row = QHBoxLayout()
        addr_row.addWidget(self.addr_label)
        addr_row.addStretch(1)
        state_box.addLayout(addr_row)
        state_box.addStretch(1)
        top.addLayout(state_box, 1)

        self.open_button = button(
            "打开网页",
            variant="accent",
            on_click=lambda: webbrowser.open(server_url()),
            icon_name="external",
            icon_color="#ffffff",
            icon_size=17,
        )
        top.addWidget(self.open_button, 0, Qt.AlignmentFlag.AlignTop)
        hero_layout.addLayout(top)

        options_row = QHBoxLayout()
        options_row.setSpacing(20)
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
        hero_layout.addLayout(options_row)
        layout.addWidget(hero)

        # ---- 控制台卡片 ----
        console_card = card(margins=(16, 14, 16, 14))
        console_layout = card_layout(console_card)
        console_layout.setSpacing(10)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        console_icon = QLabel()
        console_icon.setPixmap(pixmap("terminal", 18, PALETTE["launcher"]))
        console_icon.setFixedSize(18, 18)
        toolbar.addWidget(console_icon)
        toolbar.addWidget(label("控制台输出", "cardTitle"))
        toolbar.addStretch(1)
        self.autoscroll_box = QCheckBox("自动滚动")
        self.autoscroll_box.setChecked(bool(window.options.get("autoscroll", True)))
        self.autoscroll_box.toggled.connect(
            lambda checked: self.window.set_option("autoscroll", checked)
        )
        toolbar.addWidget(self.autoscroll_box)
        toolbar.addWidget(
            icon_button(
                "trash",
                text="清空",
                on_click=self.clear_console,
                tooltip="清空控制台输出",
            )
        )
        console_layout.addLayout(toolbar)

        self.console = ConsoleView()
        console_layout.addWidget(self.console, 1)
        layout.addWidget(console_card, 1)

        tip = hint("提示：首次使用建议先在「疑难解答」页一键扫描，确认依赖与模型就绪。")
        layout.addWidget(tip)

    # ------------------------------------------------------------------
    def _paint_state_dot(self, running: bool) -> None:
        color = PALETTE["ok"] if running else PALETTE["subtle"]
        self.state_dot.setStyleSheet(f"background: {color}; border-radius: 4px;")

    def clear_console(self) -> None:
        self.console.clear_all()

    def log(self, text: str) -> None:
        self.console.append_text(text, autoscroll=self.autoscroll_box.isChecked())

    def set_running(self, running: bool) -> None:
        if running:
            self.launch_button.setText("终 止 运 行")
            self.launch_button.setProperty("variant", "launchStop")
            apply_icon(self.launch_button, "stop", color="#ffffff", size=24)
            self.state_label.setText("运行中")
            self._set_glow_color(PALETTE["danger"])
        else:
            self.launch_button.setText("一 键 启 动")
            self.launch_button.setProperty("variant", "launch")
            apply_icon(self.launch_button, "play", color="#ffffff", size=26)
            self.state_label.setText("未运行")
            self._set_glow_color("#4f8cf7")
        self._paint_state_dot(running)
        restyle(self.launch_button)
        for box in self.option_boxes.values():
            box.setEnabled(not running)

    def _set_glow_color(self, value: str) -> None:
        tint = QColor(value)
        tint.setAlpha(150)
        self._launch_glow.setColor(tint)

    def refresh_addr(self) -> None:
        url = server_url()
        self.addr_label.setText(url)
        self.addr_label.setToolTip(f"{url}（可在「高级选项」中修改监听地址与端口）")

    def on_show(self) -> None:
        self.refresh_addr()
