"""页面：疑难解答（环境一键扫描与常用修复）。"""

from __future__ import annotations

import threading
import webbrowser

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import DOCS_URL
from ..core.system import dependency_install_tasks, scan_environment
from ..core.theme import color
from ..widgets.common import (
    button,
    card,
    card_layout,
    hint,
    label,
    page_header,
)
from ..widgets.task_dialog import TaskDialog

LEVEL_TEXT = {"ok": "✓ 正常", "warn": "⚠ 注意", "err": "✗ 异常"}
LEVEL_KEY = {"ok": "ok", "warn": "warn", "err": "err"}
LEVEL_TINT = {"warn": 26, "err": 30}


class TroubleshootPage(QWidget):
    rowReady = Signal(str, str, str)
    scanFinished = Signal()

    def __init__(self, window) -> None:
        super().__init__()
        self.window = window
        self.rowReady.connect(self._add_row)
        self.scanFinished.connect(self._on_scan_finished)
        self.scanning = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 16)
        layout.setSpacing(14)
        layout.addWidget(
            page_header("疑难解答", "一键检查运行环境，并提供常用的依赖与子模块修复")
        )

        # ---- 扫描 ----
        scan_card = card(margins=(16, 16, 16, 16))
        scan_layout = card_layout(scan_card)
        scan_layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(10)
        self.scan_button = button(
            "一键扫描",
            variant="accent",
            on_click=self.scan,
            icon_name="scan",
            icon_color="#ffffff",
            icon_size=18,
        )
        header.addWidget(self.scan_button)
        self.scan_status = label("尚未扫描", "cardHint")
        header.addWidget(self.scan_status)
        header.addStretch(1)
        scan_layout.addLayout(header)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["检查项", "结果", "说明 / 建议"])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        header_view = self.tree.header()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        scan_layout.addWidget(self.tree, 1)
        layout.addWidget(scan_card, 1)

        # ---- 常用修复 ----
        fix_card = card(margins=(16, 16, 16, 16))
        fix_layout = card_layout(fix_card)
        fix_layout.setSpacing(10)
        fix_layout.addWidget(label("常用修复", "cardTitle"))

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addWidget(
            button(
                "安装 / 修复依赖",
                on_click=self.fix_dependencies,
                icon_name="package",
                icon_size=17,
            )
        )
        actions.addWidget(
            button(
                "初始化 / 修复前端子模块",
                on_click=self.fix_submodules,
                icon_name="branch",
                icon_size=17,
            )
        )
        actions.addWidget(
            button(
                "查看官方文档",
                on_click=lambda: webbrowser.open(DOCS_URL),
                icon_name="book",
                icon_size=17,
            )
        )
        actions.addStretch(1)
        fix_layout.addLayout(actions)
        fix_layout.addWidget(
            hint(
                "「安装 / 修复依赖」优先使用 uv sync；未安装 uv 时退化为 pip install -r requirements.txt。",
                card_scoped=True,
            )
        )
        layout.addWidget(fix_card)

    # ------------------------------------------------------------------
    def scan(self) -> None:
        if self.scanning:
            return
        self.scanning = True
        self.scan_button.setEnabled(False)
        self.scan_status.setText("扫描中…")
        self.tree.clear()
        running = self.window.server.running

        def worker() -> None:
            try:
                scan_environment(
                    lambda name, level, detail: self.rowReady.emit(name, level, detail),
                    running,
                )
            except Exception as exc:  # noqa: BLE001
                self.rowReady.emit("扫描过程", "err", f"扫描时发生异常：{exc}")
            finally:
                self.scanFinished.emit()

        threading.Thread(target=worker, daemon=True).start()

    def _add_row(self, name: str, level: str, detail: str) -> None:
        item = QTreeWidgetItem([name, LEVEL_TEXT.get(level, level), detail])
        qcolor = QColor(color(LEVEL_KEY.get(level, "text")))
        item.setForeground(0, qcolor)
        item.setForeground(1, qcolor)
        item.setForeground(2, qcolor)
        tint = LEVEL_TINT.get(level)
        if tint:
            background = QColor(color(LEVEL_KEY[level]))
            background.setAlpha(tint)
            for column in range(3):
                item.setBackground(column, background)
        self.tree.addTopLevelItem(item)
        self.tree.scrollToItem(item)

    def _on_scan_finished(self) -> None:
        self.scanning = False
        self.scan_button.setEnabled(True)
        count = self.tree.topLevelItemCount()
        problems = 0
        for index in range(count):
            if self.tree.topLevelItem(index).text(1) != LEVEL_TEXT["ok"]:
                problems += 1
        if problems:
            self.scan_status.setText(f"扫描完成：{count} 项，其中 {problems} 项需要注意")
        else:
            self.scan_status.setText(f"扫描完成：{count} 项全部正常")

    def fix_dependencies(self) -> None:
        tasks = dependency_install_tasks()
        if not tasks:
            QMessageBox.critical(
                self,
                "无法安装依赖",
                "未找到可用的 Python 环境（缺少 .venv 且未安装 uv），"
                "请先安装 uv：https://docs.astral.sh/uv/",
            )
            return
        dialog = TaskDialog(
            self,
            "安装 / 修复依赖",
            tasks,
            note="正在安装项目依赖，首次安装可能需要较长时间…",
        )
        dialog.exec()
        if dialog.finished_ok:
            self.scan()

    def fix_submodules(self) -> None:
        dialog = TaskDialog(
            self,
            "初始化 / 修复前端子模块",
            [{"cmd": ["git", "submodule", "update", "--init", "--recursive"]}],
            note="正在拉取子模块内容…",
        )
        dialog.exec()
        if dialog.finished_ok:
            self.scan()

    def on_show(self) -> None:
        if not self.tree.topLevelItemCount():
            self.scan()
