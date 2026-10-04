"""页面：版本管理（查看版本、检查更新、一键更新）。"""

from __future__ import annotations

import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from ..core.system import (
    collect_git_info,
    dependency_install_tasks,
    project_python,
)
from ..widgets.common import (
    button,
    card,
    card_layout,
    hint,
    icon_button,
    label,
    page_header,
)
from ..widgets.task_dialog import TaskDialog

FIELDS = (
    ("version", "项目版本"),
    ("conf", "配置版本"),
    ("branch", "当前分支"),
    ("commit", "最新提交"),
    ("remote", "远程状态"),
)


class VersionPage(QWidget):
    infoReady = Signal(dict)

    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self.infoReady.connect(self._apply_info)
        self.value_labels: dict[str, QLabel] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 16)
        layout.setSpacing(14)
        layout.addWidget(
            page_header("版本管理", "查看当前版本与远程状态，检查并拉取最新代码")
        )

        # ---- 当前版本 ----
        info_card = card(margins=(16, 16, 16, 16))
        info_layout = card_layout(info_card)
        info_layout.setSpacing(10)

        header = QHBoxLayout()
        header.addWidget(label("当前版本信息", "cardTitle"))
        header.addStretch(1)
        header.addWidget(
            icon_button("refresh", text="刷新", on_click=self.refresh, tooltip="重新查询版本信息")
        )
        info_layout.addLayout(header)

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(8)
        for key, title in FIELDS:
            value = label("查询中…", "cardHint")
            value.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            self.value_labels[key] = value
            form.addRow(label(f"{title}："), value)
        info_layout.addLayout(form)
        layout.addWidget(info_card)

        # ---- 更新操作 ----
        update_card = card(margins=(16, 16, 16, 16))
        update_layout = card_layout(update_card)
        update_layout.setSpacing(10)
        update_layout.addWidget(label("更新操作", "cardTitle"))

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addWidget(
            button(
                "检查更新（git fetch）",
                on_click=self.check_update,
                icon_name="download",
                icon_size=17,
            )
        )
        actions.addWidget(
            button(
                "一键更新到最新版",
                variant="accent",
                on_click=self.upgrade,
                icon_name="upload",
                icon_color="#ffffff",
                icon_size=17,
            )
        )
        actions.addStretch(1)
        update_layout.addLayout(actions)
        update_layout.addWidget(
            hint(
                "「一键更新」依次执行：自动 stash 本地改动 → 拉取最新代码并更新子模块 "
                "→ 同步配置文件 → 重新安装依赖（uv sync）。",
                card_scoped=True,
            )
        )
        update_layout.addWidget(
            hint(
                "远程仓库约定：origin 指向你的 fork，upstream 指向官方仓库；"
                "可在项目目录执行 git remote -v 查看。",
                card_scoped=True,
            )
        )
        layout.addWidget(update_card)
        layout.addStretch(1)

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        def worker() -> None:
            try:
                info = collect_git_info()
            except Exception as exc:  # noqa: BLE001
                info = {"remote": f"查询失败：{exc}"}
            self.infoReady.emit(info)

        threading.Thread(target=worker, daemon=True).start()

    def _apply_info(self, info: dict) -> None:
        for key, _title in FIELDS:
            value = info.get(key)
            if value is not None:
                self.value_labels[key].setText(str(value))

    def check_update(self) -> None:
        dialog = TaskDialog(
            self,
            "检查更新",
            [{"cmd": ["git", "fetch", "--all", "--prune"]}],
            note="正在从远程仓库获取最新信息…",
            on_done=lambda _ok: self.refresh(),
        )
        dialog.exec()

    def upgrade(self) -> None:
        if self.window.server.running:
            QMessageBox.warning(
                self, "无法更新", "请先停止正在运行的服务器，再执行更新。"
            )
            return
        python = project_python()
        if not python:
            QMessageBox.critical(
                self,
                "无法更新",
                "未找到可用的 Python 环境，请先在「疑难解答」页安装依赖。",
            )
            return
        answer = QMessageBox.question(
            self,
            "确认更新",
            "将执行以下操作：\n"
            "  1. 自动 stash 本地改动\n"
            "  2. 拉取最新代码并更新子模块\n"
            "  3. 同步配置并重新安装依赖\n\n"
            "过程中请不要关闭窗口。是否继续？",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        tasks = [{"cmd": [*python, "upgrade.py"], "stdin": "y\n"}]
        tasks.extend(dependency_install_tasks())
        dialog = TaskDialog(
            self, "一键更新", tasks, note="更新过程中请勿关闭窗口。", on_done=lambda _ok: self.refresh()
        )
        dialog.exec()

    def on_show(self) -> None:
        self.refresh()
