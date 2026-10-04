"""run_server.py 进程控制：启动 / 停止 / 输出转发 / 就绪后打开浏览器。"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser

from PySide6.QtCore import QObject, Signal

from .config import conf_get
from .paths import CREATE_NO_WINDOW, IS_FROZEN, IS_WIN, ROOT, VENV_PY


class ServerController(QObject):
    """把 run_server.py 作为子进程管理，输出通过信号送回界面线程。"""

    logLine = Signal(str)
    stateChanged = Signal(bool)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.proc: subprocess.Popen | None = None

    # ------------------------------------------------------------------
    # 状态
    # ------------------------------------------------------------------
    @property
    def running(self) -> bool:
        proc = self.proc
        return proc is not None and proc.poll() is None

    # ------------------------------------------------------------------
    # 启动 / 停止
    # ------------------------------------------------------------------
    def start(
        self, verbose: bool = False, hf_mirror: bool = False, open_browser: bool = True
    ) -> bool:
        if self.running:
            return False
        cmd = self._build_cmd(verbose, hf_mirror)
        if not cmd:
            self.logLine.emit(
                "[启动器] 未找到可用的 Python 运行环境（.venv 缺失且 uv 不可用）。\n"
                "[启动器] 请到「疑难解答」页点击「安装 / 修复依赖」。\n"
            )
            return False

        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        self.logLine.emit(f"[启动器] 工作目录: {ROOT}\n")
        self.logLine.emit(f"[启动器] 执行: {' '.join(cmd)}\n")
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=CREATE_NO_WINDOW,
            )
        except Exception as exc:  # noqa: BLE001
            self.logLine.emit(f"[启动器] 启动失败: {exc}\n")
            self.proc = None
            self.stateChanged.emit(False)
            return False

        self.proc = proc
        self.stateChanged.emit(True)
        threading.Thread(target=self._pump, args=(proc,), daemon=True).start()
        if open_browser:
            threading.Thread(target=self._wait_ready_and_open, daemon=True).start()
        return True

    def stop(self) -> None:
        proc = self.proc
        if proc is None or proc.poll() is not None:
            return
        self.logLine.emit("[启动器] 正在停止服务器…\n")
        try:
            if IS_WIN:
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    capture_output=True,
                    creationflags=CREATE_NO_WINDOW,
                )
            else:
                proc.terminate()
        except Exception as exc:  # noqa: BLE001
            self.logLine.emit(f"[启动器] 停止时出错: {exc}\n")

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------
    def _build_cmd(self, verbose: bool, hf_mirror: bool) -> list[str]:
        args = ["run_server.py"]
        if verbose:
            args.append("--verbose")
        if hf_mirror:
            args.append("--hf_mirror")

        if VENV_PY.exists():
            return [str(VENV_PY), *args]
        uv = shutil.which("uv")
        if uv:
            return [uv, "run", *args]
        if not IS_FROZEN:
            return [sys.executable, *args]
        # 冻结成 exe 后 sys.executable 是启动器本身，不能再当作 Python 用
        return []

    def _pump(self, proc: subprocess.Popen) -> None:
        from .text import strip_ansi

        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                self.logLine.emit(strip_ansi(line))
        except (ValueError, OSError):
            pass
        code = proc.wait()
        if self.proc is proc:
            self.proc = None
        self.logLine.emit(f"\n[启动器] 服务器进程已退出（退出码 {code}）\n")
        self.stateChanged.emit(False)

    def _wait_ready_and_open(self) -> None:
        host = conf_get("host", "localhost") or "localhost"
        port = conf_get("port", "12393") or "12393"
        connect_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
        url = f"http://{connect_host}:{port}"
        try:
            port_int = int(port)
        except ValueError:
            return
        for _ in range(180):
            if not self.running:
                return
            try:
                with socket.create_connection((connect_host, port_int), timeout=1):
                    self.logLine.emit(f"[启动器] 服务已就绪，正在打开浏览器: {url}\n")
                    webbrowser.open(url)
                    return
            except OSError:
                time.sleep(1)
        self.logLine.emit("[启动器] 等待服务就绪超时，请手动打开网页。\n")
