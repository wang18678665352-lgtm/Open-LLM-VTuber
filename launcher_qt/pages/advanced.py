"""页面：高级选项（服务器参数、快捷打开、环境信息）。"""

from __future__ import annotations

import threading
import webbrowser

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.config import conf_get, conf_set, server_url
from ..core.paths import CONF_PATH, ROOT
from ..core.system import env_info_lines, open_path
from ..widgets.common import (
    button,
    card,
    card_layout,
    hint,
    icon_button,
    label,
    page_header,
)

SHORTCUTS: tuple[tuple[str, object, str], ...] = (
    ("编辑 conf.yaml", CONF_PATH, "file"),
    ("打开项目目录", ROOT, "folder"),
    ("角色配置目录", ROOT / "characters", "folder"),
    ("日志目录", ROOT / "logs", "folder"),
    ("模型目录", ROOT / "models", "package"),
    ("打开前端页面", None, "globe"),  # 特殊处理：走浏览器
)


class AdvancedPage(QWidget):
    envInfoReady = Signal(list)

    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self.envInfoReady.connect(self._apply_env_info)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 16)
        layout.setSpacing(14)
        layout.addWidget(
            page_header("高级选项", "修改监听地址与端口、快速打开常用目录、查看运行环境")
        )

        # ---- 服务器设置 ----
        server_card = card(margins=(16, 16, 16, 16))
        server_layout = card_layout(server_card)
        server_layout.setSpacing(10)
        server_layout.addWidget(label("服务器设置", "cardTitle"))

        form = QHBoxLayout()
        form.setSpacing(8)
        form.addWidget(label("监听地址："))
        self.host_edit = QLineEdit(conf_get("host", "localhost"))
        self.host_edit.setFixedWidth(200)
        form.addWidget(self.host_edit)
        form.addSpacing(12)
        form.addWidget(label("端口："))
        self.port_edit = QLineEdit(conf_get("port", "12393"))
        self.port_edit.setFixedWidth(90)
        form.addWidget(self.port_edit)
        form.addSpacing(8)
        form.addWidget(button("保存设置", variant="accent", on_click=self.save))
        form.addWidget(
            icon_button("refresh", text="重新读取", on_click=self.reload, tooltip="从 conf.yaml 重新读取")
        )
        form.addStretch(1)
        server_layout.addLayout(form)
        server_layout.addWidget(
            hint(
                "保存会写入 conf.yaml（首次保存前自动备份为 conf.yaml.launcher.bak），重启服务后生效。",
                card_scoped=True,
            )
        )
        layout.addWidget(server_card)

        # ---- 快捷打开 ----
        shortcut_card = card(margins=(16, 16, 16, 16))
        shortcut_layout = card_layout(shortcut_card)
        shortcut_layout.setSpacing(10)
        shortcut_layout.addWidget(label("快捷打开", "cardTitle"))
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        for index, (text, target, icon_name) in enumerate(SHORTCUTS):
            if target is None:
                handler = lambda: webbrowser.open(server_url())  # noqa: E731
            else:
                handler = lambda _=False, path=target: open_path(path)  # noqa: E731
            grid.addWidget(
                button(text, on_click=handler, icon_name=icon_name, icon_size=17),
                index // 3,
                index % 3,
            )
        for column in range(3):
            grid.setColumnStretch(column, 1)
        shortcut_layout.addLayout(grid)
        layout.addWidget(shortcut_card)

        # ---- 启动器行为 ----
        behavior_card = card(margins=(16, 16, 16, 16))
        behavior_layout = card_layout(behavior_card)
        behavior_layout.setSpacing(10)
        behavior_layout.addWidget(label("启动器行为", "cardTitle"))
        self.tray_box = QCheckBox("关闭窗口时最小化到系统托盘（而不是退出启动器）")
        self.tray_box.setChecked(bool(window.options.get("minimize_to_tray", False)))
        self.tray_box.toggled.connect(
            lambda checked: self.window.set_option("minimize_to_tray", checked)
        )
        behavior_layout.addWidget(self.tray_box)
        behavior_layout.addWidget(
            hint(
                "未开启托盘模式时，退出启动器会先确认，并在退出时同时终止服务器进程。",
                card_scoped=True,
            )
        )
        layout.addWidget(behavior_card)

        # ---- 环境信息 ----
        env_card = card(margins=(16, 16, 16, 16))
        env_layout = card_layout(env_card)
        env_layout.setSpacing(10)
        header = QHBoxLayout()
        header.addWidget(label("环境信息", "cardTitle"))
        header.addStretch(1)
        header.addWidget(
            icon_button("refresh", text="刷新", on_click=self.refresh_env, tooltip="重新收集环境信息")
        )
        env_layout.addLayout(header)

        self.env_view = QPlainTextEdit()
        self.env_view.setObjectName("envInfo")
        self.env_view.setReadOnly(True)
        self.env_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.env_view.setFixedHeight(150)
        env_layout.addWidget(self.env_view)
        layout.addWidget(env_card)
        layout.addStretch(1)

    # ------------------------------------------------------------------
    def reload(self) -> None:
        self.host_edit.setText(conf_get("host", "localhost"))
        self.port_edit.setText(conf_get("port", "12393"))

    def save(self) -> None:
        host = self.host_edit.text().strip() or "localhost"
        port_text = self.port_edit.text().strip()
        if not port_text.isdigit() or not (1 <= int(port_text) <= 65535):
            QMessageBox.critical(self, "错误", "端口必须是 1-65535 之间的数字")
            return
        ok, message = conf_set(
            {"system_config.host": host, "system_config.port": int(port_text)}
        )
        if ok:
            self.window.pages["home"].refresh_addr()
            QMessageBox.information(self, "保存成功", f"{message}\n重启服务后生效。")
        else:
            QMessageBox.critical(self, "保存失败", message)

    def refresh_env(self) -> None:
        self.env_view.setPlainText("正在收集环境信息…")

        def worker() -> None:
            try:
                lines = env_info_lines()
            except Exception as exc:  # noqa: BLE001
                lines = [f"收集环境信息失败：{exc}"]
            self.envInfoReady.emit(lines)

        threading.Thread(target=worker, daemon=True).start()

    def _apply_env_info(self, lines: list[str]) -> None:
        self.env_view.setPlainText("\n".join(lines))

    def on_show(self) -> None:
        self.reload()
        self.refresh_env()
