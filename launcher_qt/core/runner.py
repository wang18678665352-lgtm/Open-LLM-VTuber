"""后台命令序列执行器：用于更新、安装依赖等耗时任务。"""

from __future__ import annotations

import subprocess
import threading

from PySide6.QtCore import QObject, Signal

from .paths import CREATE_NO_WINDOW, IS_WIN, ROOT
from .text import strip_ansi


class CommandSequence(QObject):
    """顺序执行多组命令，实时抛出行输出，最后汇报整体成功与否。

    每个任务的格式：``{"cmd": [...], "stdin": "y\\n"（可选）}``。
    在后台线程中运行，所有 UI 更新都通过信号回到界面线程。
    """

    lineReady = Signal(str)
    finished = Signal(bool)

    def __init__(self, tasks: list[dict], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.tasks = tasks
        self.current_proc: subprocess.Popen | None = None
        self._cancelled = False
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        self._cancelled = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        """取消任务并杀掉当前命令的整个进程树。"""
        self._cancelled = True
        proc = self.current_proc
        if proc is not None and proc.poll() is None:
            try:
                if IS_WIN:
                    subprocess.run(
                        ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                        capture_output=True,
                        creationflags=CREATE_NO_WINDOW,
                    )
                else:
                    proc.terminate()
            except Exception:  # noqa: BLE001
                pass

    def _run(self) -> None:
        ok_all = True
        for index, task in enumerate(self.tasks, start=1):
            if self._cancelled:
                ok_all = False
                break
            cmd = [str(part) for part in task["cmd"]]
            stdin_data = task.get("stdin")
            self.lineReady.emit(f"\n>>> [{index}/{len(self.tasks)}] {' '.join(cmd)}\n")
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(ROOT),
                    stdin=(
                        subprocess.PIPE if stdin_data is not None else subprocess.DEVNULL
                    ),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=CREATE_NO_WINDOW,
                )
            except FileNotFoundError:
                self.lineReady.emit(f"[失败] 命令不存在: {cmd[0]}\n")
                ok_all = False
                break
            except Exception as exc:  # noqa: BLE001
                self.lineReady.emit(f"[失败] 无法执行 {cmd[0]}: {exc}\n")
                ok_all = False
                break

            self.current_proc = proc
            if stdin_data is not None and proc.stdin is not None:
                try:
                    proc.stdin.write(stdin_data)
                    proc.stdin.close()
                except (OSError, ValueError):
                    pass
            try:
                assert proc.stdout is not None
                for line in proc.stdout:
                    self.lineReady.emit(strip_ansi(line))
            except (ValueError, OSError):
                pass
            code = proc.wait()
            self.current_proc = None
            if self._cancelled:
                self.lineReady.emit("\n[已取消]\n")
                ok_all = False
                break
            if code != 0:
                self.lineReady.emit(f"\n[失败] 命令退出码 {code}\n")
                ok_all = False
                break
            self.lineReady.emit("[完成]\n")
        self.finished.emit(ok_all)
