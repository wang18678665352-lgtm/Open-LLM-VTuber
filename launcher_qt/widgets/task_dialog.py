"""耗时任务对话框：顺序执行命令并实时显示输出。"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QDialog, QHBoxLayout, QMessageBox, QVBoxLayout

from ..core.runner import CommandSequence
from ..core.theme import apply_native_chrome
from .common import button, label
from .console import ConsoleView


class TaskDialog(QDialog):
    """执行任务序列，实时打印输出；运行中关闭需要确认。"""

    def __init__(
        self,
        parent,
        title: str,
        tasks: list[dict],
        note: str = "",
        on_done: Callable[[bool], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(780, 480)
        self.setMinimumSize(600, 360)

        self.note = note
        self.on_done = on_done
        self.finished_ok: bool | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.console = ConsoleView(self)
        layout.addWidget(self.console, 1)

        bottom = QHBoxLayout()
        self.status_label = label("正在运行…")
        self.status_label.setObjectName("hint")
        bottom.addWidget(self.status_label)
        bottom.addStretch(1)
        self.close_button = button("取消", on_click=self.close)
        bottom.addWidget(self.close_button)
        layout.addLayout(bottom)

        self.sequence = CommandSequence(tasks, self)
        self.sequence.lineReady.connect(self.console.append_text)
        self.sequence.finished.connect(self._on_finished)
        self.sequence.start()

    # ------------------------------------------------------------------
    def _on_finished(self, ok: bool) -> None:
        self.finished_ok = ok
        self.status_label.setText("已完成" if ok else "失败")
        self.close_button.setText("关闭")
        self.close_button.setProperty("variant", "accent")
        self.close_button.style().unpolish(self.close_button)
        self.close_button.style().polish(self.close_button)
        if ok and self.note:
            self.console.append_text(f"\n[启动器] {self.note}\n")
        if self.on_done is not None:
            try:
                self.on_done(ok)
            except Exception:  # noqa: BLE001
                pass

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        apply_native_chrome(self, dark=False)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self.sequence.is_running:
            answer = QMessageBox.question(
                self,
                "确认",
                "任务仍在运行，确定要取消吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.sequence.cancel()
        event.accept()
