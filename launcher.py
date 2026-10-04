#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Open-LLM-VTuber 启动器
======================
仿秋叶启动器（绘世）风格的图形化一键启动工具。

- 仅使用 Python 标准库（tkinter），无需安装额外依赖
- 双击 ``启动器.bat`` 使用（自动优先使用项目 .venv 中的 Python 运行）
"""

from __future__ import annotations

import json
import os
import queue
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent
IS_WIN = os.name == "nt"
VENV_PY = (
    (ROOT / ".venv" / "Scripts" / "python.exe")
    if IS_WIN
    else (ROOT / ".venv" / "bin" / "python")
)
CONF_PATH = ROOT / "conf.yaml"
CONF_BAK_PATH = ROOT / "conf.yaml.launcher.bak"
SETTINGS_PATH = ROOT / "launcher_settings.json"
CREATE_NO_WINDOW = 0x08000000 if IS_WIN else 0
APP_VERSION = "1.0.0"
GITHUB_URL = "https://github.com/Open-LLM-VTuber/Open-LLM-VTuber"
DOCS_URL = "https://open-llm-vtuber.github.io/"

FONT_UI = "Microsoft YaHei UI"
FONT_MONO = "Consolas"

C = {
    "bg": "#17171f",
    "sidebar": "#121219",
    "panel": "#1f1f2b",
    "panel_alt": "#262636",
    "fg": "#e8e8f2",
    "subtle": "#9a9ab2",
    "accent": "#3b82f6",
    "accent_hover": "#5c9bff",
    "danger": "#e5484d",
    "danger_hover": "#f06a6e",
    "ok": "#4cc38a",
    "warn": "#e5c07b",
    "err": "#e06c75",
    "console_bg": "#0f0f16",
    "console_fg": "#d5d5e2",
    "border": "#2c2c3c",
    "launcher": "#7aa2f7",
    "entry_bg": "#14141d",
}

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")
LEVEL_RE = re.compile(
    r"\|\s*(TRACE|DEBUG|INFO|SUCCESS|WARNING|ERROR|CRITICAL)\s*\|"
)

# ---------------------------------------------------------------------------
# 通用工具函数
# ---------------------------------------------------------------------------


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def run_quiet(cmd, timeout=30):
    """静默执行命令，返回 (returncode, 合并输出)。"""
    try:
        proc = subprocess.run(
            [str(c) for c in cmd],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except FileNotFoundError:
        return -1, f"命令不存在: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, f"命令超时: {' '.join(map(str, cmd))}"
    except Exception as exc:  # noqa: BLE001
        return -1, str(exc)


def project_version() -> str:
    try:
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
        return match.group(1) if match else "未知"
    except OSError:
        return "未知"


def conf_get(key: str, default: str = "") -> str:
    """从 conf.yaml 中按行正则读取顶层/二级键的值（去掉引号与行尾注释）。"""
    if not CONF_PATH.exists():
        return default
    try:
        text = CONF_PATH.read_text(encoding="utf-8")
    except OSError:
        return default
    match = re.search(
        rf"(?m)^[ \t]*{re.escape(key)}[ \t]*:[ \t]*['\"]?([^'\"\n#]+)", text
    )
    return match.group(1).strip() if match else default


def _backup_conf() -> None:
    if CONF_PATH.exists() and not CONF_BAK_PATH.exists():
        try:
            shutil.copy2(CONF_PATH, CONF_BAK_PATH)
        except OSError:
            pass


def conf_set(updates: dict):
    """把 {"system_config.port": 12393} 形式的更新写回 conf.yaml，保留注释。

    优先使用 ruamel.yaml（项目依赖，保留注释与格式）；
    若启动器未运行在项目 venv 中，退化为定点正则替换。
    """
    if not CONF_PATH.exists():
        return False, "conf.yaml 不存在"
    try:
        text = CONF_PATH.read_text(encoding="utf-8")
    except OSError as exc:
        return False, str(exc)

    _backup_conf()

    try:
        from ruamel.yaml import YAML
    except ImportError:
        new_text = text
        for dotted, value in updates.items():
            _, key = dotted.split(".", 1)
            if isinstance(value, int):
                pattern = rf"(?m)^([ \t]*{re.escape(key)}[ \t]*:[ \t]*)\d+"
                new_text, n = re.subn(pattern, rf"\g<1>{value}", new_text, count=1)
            else:
                pattern = rf"(?m)^([ \t]*{re.escape(key)}[ \t]*:[ \t]*)['\"]?[^'\"\n#]*['\"]?"
                new_text, n = re.subn(
                    pattern, lambda m: f"{m.group(1)}'{value}'", new_text, count=1
                )
            if n == 0:
                return False, f"未能在 conf.yaml 中找到配置项: {dotted}"
        try:
            with open(CONF_PATH, "w", encoding="utf-8", newline="") as f:
                f.write(new_text)
        except OSError as exc:
            return False, str(exc)
        return True, "已保存（正则模式）"

    try:
        yaml = YAML()
        yaml.preserve_quotes = True
        data = yaml.load(text)
        for dotted, value in updates.items():
            section, key = dotted.split(".", 1)
            if data.get(section) is None:
                data[section] = {}
            data[section][key] = value
        with open(CONF_PATH, "w", encoding="utf-8", newline="") as f:
            yaml.dump(data, f)
        return True, "已保存"
    except Exception as exc:  # noqa: BLE001
        return False, f"写入 conf.yaml 失败: {exc}"


def server_url() -> str:
    host = conf_get("host", "localhost") or "localhost"
    port = conf_get("port", "12393") or "12393"
    connect_host = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    return f"http://{connect_host}:{port}"


def open_path(path) -> None:
    path = str(path)
    if IS_WIN:
        os.startfile(path)  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def load_settings() -> dict:
    defaults = {
        "verbose": False,
        "hf_mirror": False,
        "open_browser": True,
        "autoscroll": True,
    }
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            defaults.update({k: bool(v) for k, v in data.items() if k in defaults})
    except (OSError, ValueError):
        pass
    return defaults


def save_settings(settings: dict) -> None:
    try:
        SETTINGS_PATH.write_text(
            json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


# ---------------------------------------------------------------------------
# 服务器进程控制
# ---------------------------------------------------------------------------


class ServerController:
    """负责启动/停止 run_server.py 并把输出推入事件队列。"""

    def __init__(self, events: queue.Queue):
        self.events = events
        self.proc: subprocess.Popen | None = None

    @property
    def running(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self, verbose=False, hf_mirror=False, open_browser=True) -> None:
        if self.running:
            return
        cmd = self._build_cmd(verbose, hf_mirror)
        env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        self.events.put(("log", f"[启动器] 执行: {' '.join(cmd)}\n"))
        try:
            self.proc = subprocess.Popen(
                cmd,
                cwd=ROOT,
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
            self.events.put(("log", f"[启动器] 启动失败: {exc}\n"))
            self.proc = None
            self.events.put(("state", "stopped"))
            return
        self.events.put(("state", "running"))
        threading.Thread(target=self._pump, daemon=True).start()
        if open_browser:
            threading.Thread(target=self._wait_ready_and_open, daemon=True).start()

    def stop(self) -> None:
        if not self.running:
            return
        self.events.put(("log", "[启动器] 正在停止服务器…\n"))
        try:
            if IS_WIN:
                subprocess.run(
                    ["taskkill", "/PID", str(self.proc.pid), "/T", "/F"],
                    capture_output=True,
                    creationflags=CREATE_NO_WINDOW,
                )
            else:
                self.proc.terminate()
        except Exception as exc:  # noqa: BLE001
            self.events.put(("log", f"[启动器] 停止时出错: {exc}\n"))

    def _build_cmd(self, verbose: bool, hf_mirror: bool) -> list:
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
        return [sys.executable, *args]

    def _pump(self) -> None:
        proc = self.proc
        try:
            for line in proc.stdout:
                self.events.put(("log", strip_ansi(line)))
        except (ValueError, OSError):
            pass
        code = proc.wait()
        if self.proc is proc:
            self.proc = None
        self.events.put(("log", f"\n[启动器] 服务器进程已退出（退出码 {code}）\n"))
        self.events.put(("state", "stopped"))

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
                    self.events.put(
                        ("log", f"[启动器] 服务已就绪，正在打开浏览器: {url}\n")
                    )
                    webbrowser.open(url)
                    return
            except OSError:
                time.sleep(1)
        self.events.put(("log", "[启动器] 等待服务就绪超时，请手动打开网页。\n"))


# ---------------------------------------------------------------------------
# 耗时任务窗口（更新 / 安装依赖等）
# ---------------------------------------------------------------------------


class TaskWindow(tk.Toplevel):
    """顺序执行一组命令并实时展示输出。"""

    def __init__(self, app, title, tasks, note="", on_done=None):
        super().__init__(app)
        self.app = app
        self.on_done = on_done
        self.note = note
        self.tasks = tasks
        self.q: queue.Queue = queue.Queue()
        self.current_proc: subprocess.Popen | None = None
        self.finished = False

        self.title(title)
        self.geometry("780x480")
        self.minsize(600, 360)
        self.configure(bg=C["bg"])
        self.transient(app)

        frame, self.text = make_console(self)
        frame.pack(fill="both", expand=True, padx=12, pady=(12, 6))

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=12, pady=(0, 12))
        self.status_label = ttk.Label(bottom, text="正在运行…", style="Subtle.TLabel")
        self.status_label.pack(side="left")
        self.close_btn = ttk.Button(bottom, text="取消", command=self._on_close)
        self.close_btn.pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        threading.Thread(target=self._run, daemon=True).start()
        self.after(100, self._poll)

    def _run(self) -> None:
        ok_all = True
        for i, task in enumerate(self.tasks, 1):
            cmd = [str(c) for c in task["cmd"]]
            stdin_data = task.get("stdin")
            self.q.put(("line", f"\n>>> [{i}/{len(self.tasks)}] {' '.join(cmd)}\n"))
            try:
                proc = subprocess.Popen(
                    cmd,
                    cwd=ROOT,
                    stdin=subprocess.PIPE if stdin_data is not None else subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    creationflags=CREATE_NO_WINDOW,
                )
            except FileNotFoundError:
                self.q.put(("line", f"[失败] 命令不存在: {cmd[0]}\n"))
                ok_all = False
                break
            self.current_proc = proc
            if stdin_data is not None:
                try:
                    proc.stdin.write(stdin_data)
                    proc.stdin.close()
                except (OSError, ValueError):
                    pass
            try:
                for line in proc.stdout:
                    self.q.put(("line", strip_ansi(line)))
            except (ValueError, OSError):
                pass
            rc = proc.wait()
            self.current_proc = None
            if rc != 0:
                self.q.put(("line", f"\n[失败] 命令退出码 {rc}\n"))
                ok_all = False
                break
            self.q.put(("line", "[完成]\n"))
        self.q.put(("done", ok_all))

    def _poll(self) -> None:
        if not self.winfo_exists():
            return
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "line":
                    append_console(self.text, payload)
                elif kind == "done":
                    self.finished = True
                    ok = bool(payload)
                    self.status_label.config(text="已完成" if ok else "失败")
                    self.close_btn.config(text="关闭")
                    if ok and self.note:
                        append_console(self.text, f"\n[启动器] {self.note}\n")
                    if self.on_done:
                        try:
                            self.on_done(ok)
                        except Exception:  # noqa: BLE001
                            pass
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _on_close(self) -> None:
        if not self.finished:
            if not messagebox.askyesno("确认", "任务仍在运行，确定要取消吗？", parent=self):
                return
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
                except OSError:
                    pass
        self.finished = True
        self.destroy()


# ---------------------------------------------------------------------------
# 控制台组件
# ---------------------------------------------------------------------------

LEVEL_TAGS = {
    "TRACE": "debug",
    "DEBUG": "debug",
    "INFO": "info",
    "SUCCESS": "success",
    "WARNING": "warn",
    "ERROR": "err",
    "CRITICAL": "err",
}


def make_console(parent, height=10):
    """创建深色控制台 Text 组件，返回 (外框, Text)。"""
    frame = tk.Frame(
        parent,
        bg=C["console_bg"],
        highlightbackground=C["border"],
        highlightthickness=1,
    )
    text = tk.Text(
        frame,
        bg=C["console_bg"],
        fg=C["console_fg"],
        insertbackground="#ffffff",
        selectbackground=C["accent"],
        font=(FONT_MONO, 10),
        wrap="none",
        state="disabled",
        relief="flat",
        height=height,
    )
    vsb = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
    hsb = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)
    text.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    text.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)

    text.tag_configure("info", foreground=C["ok"])
    text.tag_configure("success", foreground="#56c8d8")
    text.tag_configure("warn", foreground=C["warn"])
    text.tag_configure("err", foreground=C["err"])
    text.tag_configure("debug", foreground="#6b7280")
    text.tag_configure("launcher", foreground=C["launcher"])
    return frame, text


def _line_tag(line: str):
    if line.startswith("[启动器]") or line.startswith(">>>"):
        return "launcher"
    match = LEVEL_RE.search(line)
    if match:
        return LEVEL_TAGS.get(match.group(1))
    return ()


def append_console(text: tk.Text, s: str, autoscroll=True, max_lines=6000) -> None:
    text.configure(state="normal")
    for line in s.splitlines(keepends=True):
        text.insert("end", line, _line_tag(line))
    # 限制最大行数，防止长时间运行占用过多内存
    line_count = int(text.index("end-1c").split(".")[0])
    if line_count > max_lines:
        text.delete("1.0", f"{line_count - max_lines}.0")
    text.configure(state="disabled")
    if autoscroll:
        text.see("end")


# ---------------------------------------------------------------------------
# 页面：一键启动
# ---------------------------------------------------------------------------


class HomePage(ttk.Frame):
    def __init__(self, app, parent):
        super().__init__(parent, padding=16)
        self.app = app
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        ttk.Label(self, text="一键启动", style="PageTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )

        # ---- 启动卡片 ----
        card = ttk.Frame(self, style="Card.TFrame", padding=16)
        card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        card.columnconfigure(1, weight=1)

        self.launch_btn = ttk.Button(
            card, text="一 键 启 动", style="Launch.TButton", command=app.toggle_server
        )
        self.launch_btn.grid(row=0, column=0, rowspan=3, sticky="ns", padx=(0, 20))

        self.state_label = ttk.Label(card, text="状态：未运行", style="Card.TLabel")
        self.state_label.grid(row=0, column=1, sticky="w")
        self.addr_label = ttk.Label(
            card, text=f"地址：{server_url()}", style="CardSubtle.TLabel"
        )
        self.addr_label.grid(row=1, column=1, sticky="w")

        open_btn = ttk.Button(
            card, text="打开网页", command=lambda: webbrowser.open(server_url())
        )
        open_btn.grid(row=0, column=2, rowspan=2, sticky="e", padx=(8, 0))

        opts = ttk.Frame(card, style="Card.TFrame")
        opts.grid(row=2, column=1, columnspan=2, sticky="ew", pady=(10, 0))
        self.verbose_cb = ttk.Checkbutton(
            opts,
            text="详细日志 (--verbose)",
            style="Card.TCheckbutton",
            variable=app.opt_verbose,
            command=app.save_settings,
        )
        self.verbose_cb.pack(side="left", padx=(0, 16))
        self.hf_cb = ttk.Checkbutton(
            opts,
            text="HF 镜像加速 (--hf_mirror)",
            style="Card.TCheckbutton",
            variable=app.opt_hf_mirror,
            command=app.save_settings,
        )
        self.hf_cb.pack(side="left", padx=(0, 16))
        self.open_cb = ttk.Checkbutton(
            opts,
            text="启动后自动打开浏览器",
            style="Card.TCheckbutton",
            variable=app.opt_open_browser,
            command=app.save_settings,
        )
        self.open_cb.pack(side="left")

        # ---- 控制台 ----
        console_card = ttk.Frame(self, style="Card.TFrame", padding=(12, 8))
        console_card.grid(row=2, column=0, sticky="nsew")
        console_card.columnconfigure(0, weight=1)
        console_card.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(console_card, style="Card.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        ttk.Label(toolbar, text="控制台输出", style="CardTitle.TLabel").pack(side="left")
        ttk.Button(toolbar, text="清空", command=self.clear_console).pack(side="right")
        ttk.Checkbutton(
            toolbar,
            text="自动滚动",
            style="Card.TCheckbutton",
            variable=app.opt_autoscroll,
            command=app.save_settings,
        ).pack(side="right", padx=(0, 10))

        frame, self.console = make_console(console_card)
        frame.grid(row=1, column=0, sticky="nsew")

    def clear_console(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")

    def log(self, s: str):
        append_console(self.console, s, autoscroll=self.app.opt_autoscroll.get())

    def set_running(self, running: bool):
        if running:
            self.launch_btn.config(text="终 止 运 行", style="LaunchStop.TButton")
            self.state_label.config(text="状态：运行中")
        else:
            self.launch_btn.config(text="一 键 启 动", style="Launch.TButton")
            self.state_label.config(text="状态：未运行")
        for cb in (self.verbose_cb, self.hf_cb, self.open_cb):
            cb.state(["disabled"] if running else ["!disabled"])

    def refresh_addr(self):
        self.addr_label.config(text=f"地址：{server_url()}")


# ---------------------------------------------------------------------------
# 页面：高级选项
# ---------------------------------------------------------------------------


class AdvancedPage(ttk.Frame):
    def __init__(self, app, parent):
        super().__init__(parent, padding=16)
        self.app = app
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text="高级选项", style="PageTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )

        # ---- 服务器设置 ----
        card = ttk.Frame(self, style="Card.TFrame", padding=16)
        card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(card, text="服务器设置", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=6, sticky="w", pady=(0, 10)
        )

        ttk.Label(card, text="监听地址：", style="Card.TLabel").grid(
            row=1, column=0, sticky="w"
        )
        self.host_var = tk.StringVar(value=conf_get("host", "localhost"))
        ttk.Entry(card, textvariable=self.host_var, width=24).grid(
            row=1, column=1, sticky="w", padx=(4, 20)
        )
        ttk.Label(card, text="端口：", style="Card.TLabel").grid(row=1, column=2, sticky="w")
        self.port_var = tk.StringVar(value=conf_get("port", "12393"))
        ttk.Entry(card, textvariable=self.port_var, width=8).grid(
            row=1, column=3, sticky="w", padx=(4, 20)
        )
        ttk.Button(card, text="保存设置", style="Accent.TButton", command=self.save).grid(
            row=1, column=4, padx=(0, 8)
        )
        ttk.Button(card, text="重新读取", command=self.reload).grid(row=1, column=5)
        ttk.Label(
            card,
            text="保存会写入 conf.yaml（首次保存前自动备份为 conf.yaml.launcher.bak），重启服务后生效。",
            style="CardSubtle.TLabel",
        ).grid(row=2, column=0, columnspan=6, sticky="w", pady=(10, 0))

        # ---- 快捷打开 ----
        card2 = ttk.Frame(self, style="Card.TFrame", padding=16)
        card2.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(card2, text="快捷打开", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10)
        )
        shortcuts = [
            ("编辑 conf.yaml", lambda: open_path(CONF_PATH)),
            ("打开项目目录", lambda: open_path(ROOT)),
            ("角色配置目录", lambda: open_path(ROOT / "characters")),
            ("日志目录", lambda: open_path(ROOT / "logs")),
            ("模型目录", lambda: open_path(ROOT / "models")),
            ("打开前端页面", lambda: webbrowser.open(server_url())),
        ]
        for i, (label, cmd) in enumerate(shortcuts):
            ttk.Button(card2, text=label, command=cmd).grid(
                row=1 + i // 3, column=i % 3, sticky="ew", padx=(0, 10), pady=4
            )
        for col in range(3):
            card2.columnconfigure(col, weight=1)

        # ---- 环境信息 ----
        card3 = ttk.Frame(self, style="Card.TFrame", padding=16)
        card3.grid(row=3, column=0, sticky="ew")
        ttk.Label(card3, text="环境信息", style="CardTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )
        self.env_text = tk.Text(
            card3,
            bg=C["panel"],
            fg=C["fg"],
            relief="flat",
            height=6,
            font=(FONT_UI, 10),
            state="disabled",
            highlightthickness=0,
        )
        self.env_text.grid(row=1, column=0, sticky="ew")

    def reload(self):
        self.host_var.set(conf_get("host", "localhost"))
        self.port_var.set(conf_get("port", "12393"))

    def save(self):
        host = self.host_var.get().strip() or "localhost"
        port_s = self.port_var.get().strip()
        if not port_s.isdigit() or not (1 <= int(port_s) <= 65535):
            messagebox.showerror("错误", "端口必须是 1-65535 之间的数字", parent=self)
            return
        ok, msg = conf_set(
            {"system_config.host": host, "system_config.port": int(port_s)}
        )
        if ok:
            self.app.pages["home"].refresh_addr()
            messagebox.showinfo("保存成功", f"{msg}\n重启服务后生效。", parent=self)
        else:
            messagebox.showerror("保存失败", msg, parent=self)

    def on_show(self):
        lines = []

        def add(k, v):
            lines.append(f"{k:<14}{v}")

        add("启动器 Python", f"{sys.executable} ({sys.version.split()[0]})")
        if VENV_PY.exists():
            rc, out = run_quiet([str(VENV_PY), "--version"])
            add("项目 Python", f"{VENV_PY} ({out.strip() if rc == 0 else '异常'})")
        else:
            add("项目 Python", ".venv 不存在，请先在「疑难解答」页安装依赖")
        uv = shutil.which("uv")
        if uv:
            rc, out = run_quiet([uv, "--version"])
            add("uv", out.strip() if rc == 0 else uv)
        else:
            add("uv", "未安装（https://docs.astral.sh/uv/）")
        add("项目版本", f"v{project_version()}")
        add("配置文件版本", conf_get("conf_version", "未知"))
        add("前端地址", server_url())

        self.env_text.configure(state="normal")
        self.env_text.delete("1.0", "end")
        self.env_text.insert("1.0", "\n".join(lines))
        self.env_text.configure(state="disabled")


# ---------------------------------------------------------------------------
# 页面：版本管理
# ---------------------------------------------------------------------------


class VersionPage(ttk.Frame):
    def __init__(self, app, parent):
        super().__init__(parent, padding=16)
        self.app = app
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text="版本管理", style="PageTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )

        card = ttk.Frame(self, style="Card.TFrame", padding=16)
        card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        card.columnconfigure(1, weight=1)
        ttk.Label(card, text="当前版本信息", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10)
        )

        self.info_labels = {}
        rows = [
            ("version", "项目版本"),
            ("conf", "配置文件版本"),
            ("branch", "当前分支"),
            ("commit", "最近提交"),
            ("remote", "远程状态"),
        ]
        for i, (key, label) in enumerate(rows, start=1):
            ttk.Label(card, text=f"{label}：", style="Card.TLabel").grid(
                row=i, column=0, sticky="nw", pady=2
            )
            value = ttk.Label(card, text="…", style="CardSubtle.TLabel", wraplength=640)
            value.grid(row=i, column=1, sticky="w", pady=2)
            self.info_labels[key] = value

        ttk.Button(card, text="刷新", command=self.refresh).grid(
            row=1, column=2, rowspan=2, sticky="ne", padx=(10, 0)
        )

        card2 = ttk.Frame(self, style="Card.TFrame", padding=16)
        card2.grid(row=2, column=0, sticky="ew")
        ttk.Label(card2, text="更新操作", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )
        ttk.Button(card2, text="检查更新（git fetch）", command=self.check_update).grid(
            row=1, column=0, sticky="w", padx=(0, 10)
        )
        ttk.Button(
            card2,
            text="一键更新到最新版",
            style="Accent.TButton",
            command=self.upgrade,
        ).grid(row=1, column=1, sticky="w")
        ttk.Label(
            card2,
            text="一键更新将执行官方 upgrade.py（自动 stash 本地改动 → git pull → 更新子模块 → 同步配置），随后执行 uv sync 更新依赖。",
            style="CardSubtle.TLabel",
            wraplength=760,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def on_show(self):
        self.refresh()

    def refresh(self):
        def worker():
            info = {
                "version": f"v{project_version()}",
                "conf": conf_get("conf_version", "未知"),
            }
            rc, branch = run_quiet(["git", "branch", "--show-current"])
            info["branch"] = branch.strip() if rc == 0 and branch.strip() else "（非 git 仓库或 git 不可用）"
            rc, commit = run_quiet(["git", "log", "-1", "--format=%h  %s  (%cr)"])
            info["commit"] = commit.strip() if rc == 0 else "未知"
            rc, counts = run_quiet(
                ["git", "rev-list", "--left-right", "--count", "HEAD...@{upstream}"]
            )
            if rc == 0 and counts.strip():
                try:
                    ahead, behind = map(int, counts.split())
                    if behind > 0:
                        info["remote"] = f"落后远程 {behind} 个提交，可更新"
                    elif ahead > 0:
                        info["remote"] = f"领先远程 {ahead} 个提交（本地有未推送改动）"
                    else:
                        info["remote"] = "已是最新"
                except ValueError:
                    info["remote"] = counts.strip()
            else:
                info["remote"] = "未配置上游分支，无法比较（可尝试「检查更新」）"
            self.app.events.put(("gitinfo", info))

        threading.Thread(target=worker, daemon=True).start()

    def apply_info(self, info: dict):
        for key, label in self.info_labels.items():
            label.config(text=info.get(key, "未知"))

    def check_update(self):
        TaskWindow(
            self.app,
            "检查更新",
            [{"cmd": ["git", "fetch"]}],
            note="已拉取远程信息，请查看「远程状态」。",
            on_done=lambda ok: self.refresh(),
        )

    def upgrade(self):
        if self.app.server.running:
            messagebox.showwarning(
                "提示", "请先停止正在运行的服务器，再执行更新。", parent=self
            )
            return
        if not messagebox.askyesno(
            "确认更新",
            "即将更新到最新版：\n\n"
            "1. 本地未提交的改动会被自动 stash 并在更新后恢复\n"
            "2. 拉取最新代码并更新子模块\n"
            "3. 同步配置文件并执行 uv sync 更新依赖\n\n"
            "确定继续吗？",
            parent=self,
        ):
            return
        py = str(VENV_PY) if VENV_PY.exists() else sys.executable
        tasks = [{"cmd": [py, "upgrade.py"], "stdin": "y\n"}]
        uv = shutil.which("uv")
        if uv:
            tasks.append({"cmd": [uv, "sync"]})
        else:
            tasks.append({"cmd": [py, "-m", "pip", "install", "-r", "requirements.txt"]})
        TaskWindow(
            self.app,
            "一键更新",
            tasks,
            note="更新完成，重启服务后生效。",
            on_done=lambda ok: self.refresh(),
        )


# ---------------------------------------------------------------------------
# 页面：疑难解答
# ---------------------------------------------------------------------------


class TroubleshootPage(ttk.Frame):
    def __init__(self, app, parent):
        super().__init__(parent, padding=16)
        self.app = app
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        ttk.Label(self, text="疑难解答", style="PageTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )

        toolbar = ttk.Frame(self)
        toolbar.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(
            toolbar, text="一键扫描", style="Accent.TButton", command=self.scan
        ).pack(side="left")
        ttk.Label(
            toolbar,
            text="扫描本机环境，定位常见启动问题",
            style="Subtle.TLabel",
        ).pack(side="left", padx=(12, 0))

        tree_frame = ttk.Frame(self)
        tree_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 12))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("item", "result", "detail"),
            show="headings",
            height=12,
        )
        self.tree.heading("item", text="检查项")
        self.tree.heading("result", text="结果")
        self.tree.heading("detail", text="说明 / 建议")
        self.tree.column("item", width=180, anchor="w")
        self.tree.column("result", width=80, anchor="center")
        self.tree.column("detail", width=520, anchor="w")
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.tag_configure("ok", foreground=C["ok"])
        self.tree.tag_configure("warn", foreground=C["warn"])
        self.tree.tag_configure("err", foreground=C["err"])

        card = ttk.Frame(self, style="Card.TFrame", padding=16)
        card.grid(row=3, column=0, sticky="ew")
        ttk.Label(card, text="常用修复", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10)
        )
        ttk.Button(card, text="安装 / 修复依赖（uv sync）", command=self.fix_deps).grid(
            row=1, column=0, sticky="w", padx=(0, 10)
        )
        ttk.Button(
            card, text="初始化 / 修复前端子模块", command=self.fix_submodule
        ).grid(row=1, column=1, sticky="w", padx=(0, 10))
        ttk.Button(card, text="查看官方文档", command=lambda: webbrowser.open(DOCS_URL)).grid(
            row=1, column=2, sticky="w"
        )

    def scan(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _scan_worker(self):
        put = lambda name, level, detail: self.app.events.put(
            ("scan", (name, level, detail))
        )

        # 1. 项目虚拟环境
        if VENV_PY.exists():
            rc, out = run_quiet(
                [
                    str(VENV_PY),
                    "-c",
                    "import sys;print('%d.%d.%d' % sys.version_info[:3])",
                ]
            )
            ver = out.strip().splitlines()[-1] if out.strip() else "未知"
            try:
                major, minor = ver.split(".")[:2]
                ok = major == "3" and 10 <= int(minor) <= 12
            except (ValueError, IndexError):
                ok = False
            if rc == 0 and ok:
                put("Python 版本", "ok", f".venv 中的 Python {ver} 符合要求（>=3.10,<3.13）")
            else:
                put(
                    "Python 版本",
                    "err",
                    f".venv 中的 Python {ver} 不符合要求（需要 >=3.10,<3.13），建议删除 .venv 后重新安装依赖",
                )
        else:
            put("Python 虚拟环境", "err", ".venv 不存在，请点击下方「安装 / 修复依赖」")

        # 2. uv
        uv = shutil.which("uv")
        if uv:
            rc, out = run_quiet([uv, "--version"])
            put("uv 包管理器", "ok" if rc == 0 else "warn", out.strip() if rc == 0 else "uv 存在但无法执行")
        else:
            put("uv 包管理器", "warn", "未安装 uv；安装依赖与更新将退化到 pip，速度较慢")

        # 3. 关键依赖可导入
        if VENV_PY.exists():
            rc, out = run_quiet(
                [
                    str(VENV_PY),
                    "-c",
                    "import fastapi, loguru, yaml, uvicorn, openai, sherpa_onnx",
                ],
                timeout=90,
            )
            if rc == 0:
                put("关键依赖", "ok", "fastapi / loguru / uvicorn / openai / sherpa-onnx 均可导入")
            else:
                tail = out.strip().splitlines()[-1] if out.strip() else ""
                put("关键依赖", "err", f"依赖缺失或损坏（{tail}），请点击「安装 / 修复依赖」")

        # 4. conf.yaml
        if CONF_PATH.exists():
            put("配置文件", "ok", f"conf.yaml 存在（配置版本 {conf_get('conf_version', '未知')}）")
        else:
            put(
                "配置文件",
                "err",
                "conf.yaml 不存在，请从 config_templates 目录复制一份默认配置到项目根目录",
            )

        # 5. 前端子模块
        if (ROOT / "frontend" / "index.html").exists():
            put("前端子模块", "ok", "frontend/index.html 存在")
        else:
            put("前端子模块", "err", "前端文件缺失，请点击「初始化 / 修复前端子模块」")

        # 6. Live2D 模型
        live2d_dir = ROOT / "live2d-models"
        models = [p for p in live2d_dir.iterdir() if p.is_dir()] if live2d_dir.exists() else []
        if models:
            put("Live2D 模型", "ok", f"发现 {len(models)} 个模型：{', '.join(p.name for p in models[:4])}")
        else:
            put("Live2D 模型", "err", "live2d-models 目录为空，请检查 git 子模块是否完整")

        # 7. ASR 模型
        models_dir = ROOT / "models"
        asr = list(models_dir.glob("sherpa-onnx-*")) if models_dir.exists() else []
        if asr:
            put("本地 ASR 模型", "ok", f"已下载：{asr[0].name}")
        else:
            put("本地 ASR 模型", "warn", "未检测到 sherpa-onnx 模型；若使用本地 ASR，首次启动会自动下载")

        # 8. 端口占用
        port_s = conf_get("port", "12393") or "12393"
        try:
            with socket.create_connection(("127.0.0.1", int(port_s)), timeout=1):
                if self.app.server.running:
                    put("端口占用", "ok", f"端口 {port_s} 正在被本启动器运行的服务使用")
                else:
                    put(
                        "端口占用",
                        "warn",
                        f"端口 {port_s} 已被其他程序占用，请在「高级选项」中修改端口或关闭占用程序",
                    )
        except (OSError, ValueError):
            put("端口占用", "ok", f"端口 {port_s} 空闲")

        self.app.events.put(("scan_done", None))

    def add_scan_row(self, name, level, detail):
        text = {"ok": "✓ 正常", "warn": "⚠ 注意", "err": "✗ 异常"}.get(level, level)
        self.tree.insert("", "end", values=(name, text, detail), tags=(level,))

    def fix_deps(self):
        uv = shutil.which("uv")
        if uv:
            tasks = [{"cmd": [uv, "sync"]}]
        else:
            py = str(VENV_PY) if VENV_PY.exists() else sys.executable
            tasks = [
                {"cmd": [py, "-m", "pip", "install", "-r", "requirements.txt"]}
            ]
        TaskWindow(
            self.app,
            "安装 / 修复依赖",
            tasks,
            note="依赖安装完成。",
            on_done=lambda ok: self.scan(),
        )

    def fix_submodule(self):
        TaskWindow(
            self.app,
            "初始化前端子模块",
            [{"cmd": ["git", "submodule", "update", "--init", "--recursive"]}],
            note="子模块初始化完成。",
            on_done=lambda ok: self.scan(),
        )


# ---------------------------------------------------------------------------
# 页面：关于
# ---------------------------------------------------------------------------


class AboutPage(ttk.Frame):
    def __init__(self, app, parent):
        super().__init__(parent, padding=16)
        self.columnconfigure(0, weight=1)

        ttk.Label(self, text="关于", style="PageTitle.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )

        card = ttk.Frame(self, style="Card.TFrame", padding=24)
        card.grid(row=1, column=0, sticky="ew")
        ttk.Label(
            card,
            text="Open-LLM-VTuber 启动器",
            style="CardTitle.TLabel",
            font=(FONT_UI, 14, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            card,
            text=f"启动器 v{APP_VERSION}    项目 v{project_version()}",
            style="CardSubtle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 14))
        ttk.Label(
            card,
            text=(
                "一个仿秋叶启动器（绘世）风格的图形化启动工具：\n"
                "一键启停服务、实时控制台、配置修改、版本更新与环境自检。\n\n"
                "界面灵感致敬 秋葉aaaki 的绘世启动器。\n"
                "本启动器为社区自制工具，与 Open-LLM-VTuber 官方无关。"
            ),
            style="Card.TLabel",
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(0, 14))

        links = ttk.Frame(card, style="Card.TFrame")
        links.grid(row=3, column=0, sticky="w")
        ttk.Button(
            links, text="GitHub 仓库", command=lambda: webbrowser.open(GITHUB_URL)
        ).pack(side="left", padx=(0, 10))
        ttk.Button(
            links, text="官方文档", command=lambda: webbrowser.open(DOCS_URL)
        ).pack(side="left")


# ---------------------------------------------------------------------------
# 主窗口
# ---------------------------------------------------------------------------


class LauncherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Open-LLM-VTuber 启动器")
        self.geometry("1040x680")
        self.minsize(920, 600)
        self.configure(bg=C["bg"])
        icon = ROOT / "frontend" / "favicon.ico"
        if IS_WIN and icon.exists():
            try:
                self.iconbitmap(str(icon))
            except tk.TclError:
                pass

        self.report_callback_exception = self._on_callback_error

        self.settings = load_settings()
        self.opt_verbose = tk.BooleanVar(value=self.settings["verbose"])
        self.opt_hf_mirror = tk.BooleanVar(value=self.settings["hf_mirror"])
        self.opt_open_browser = tk.BooleanVar(value=self.settings["open_browser"])
        self.opt_autoscroll = tk.BooleanVar(value=self.settings["autoscroll"])

        self.events: queue.Queue = queue.Queue()
        self.server = ServerController(self.events)

        self._setup_style()
        self._build_layout()
        self.show_page("home")

        self.after(100, self._poll_events)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- UI 构建 ----

    def _setup_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        self.option_add("*Font", (FONT_UI, 10))

        style.configure("TFrame", background=C["bg"])
        style.configure("Sidebar.TFrame", background=C["sidebar"])
        style.configure("Card.TFrame", background=C["panel"])

        style.configure("TLabel", background=C["bg"], foreground=C["fg"])
        style.configure("Subtle.TLabel", background=C["bg"], foreground=C["subtle"])
        style.configure(
            "PageTitle.TLabel",
            background=C["bg"],
            foreground=C["fg"],
            font=(FONT_UI, 16, "bold"),
        )
        style.configure(
            "SidebarTitle.TLabel",
            background=C["sidebar"],
            foreground=C["fg"],
            font=(FONT_UI, 13, "bold"),
        )
        style.configure(
            "SidebarSub.TLabel",
            background=C["sidebar"],
            foreground=C["subtle"],
            font=(FONT_UI, 9),
        )
        style.configure("Card.TLabel", background=C["panel"], foreground=C["fg"])
        style.configure(
            "CardSubtle.TLabel", background=C["panel"], foreground=C["subtle"]
        )
        style.configure(
            "CardTitle.TLabel",
            background=C["panel"],
            foreground=C["fg"],
            font=(FONT_UI, 11, "bold"),
        )

        style.configure(
            "TButton",
            background=C["panel_alt"],
            foreground=C["fg"],
            borderwidth=0,
            padding=(14, 7),
        )
        style.map(
            "TButton",
            background=[("active", C["border"]), ("disabled", C["panel"])],
            foreground=[("disabled", C["subtle"])],
        )
        style.configure(
            "Accent.TButton", background=C["accent"], foreground="#ffffff"
        )
        style.map(
            "Accent.TButton",
            background=[("active", C["accent_hover"]), ("disabled", C["panel"])],
        )
        style.configure(
            "Launch.TButton",
            background=C["accent"],
            foreground="#ffffff",
            font=(FONT_UI, 15, "bold"),
            padding=(34, 26),
        )
        style.map("Launch.TButton", background=[("active", C["accent_hover"])])
        style.configure(
            "LaunchStop.TButton",
            background=C["danger"],
            foreground="#ffffff",
            font=(FONT_UI, 15, "bold"),
            padding=(34, 26),
        )
        style.map("LaunchStop.TButton", background=[("active", C["danger_hover"])])

        style.configure(
            "Nav.TButton",
            background=C["sidebar"],
            foreground=C["fg"],
            font=(FONT_UI, 11),
            padding=(18, 11),
            anchor="w",
            borderwidth=0,
        )
        style.map("Nav.TButton", background=[("active", C["panel_alt"])])
        style.configure(
            "NavSel.TButton",
            background=C["accent"],
            foreground="#ffffff",
            font=(FONT_UI, 11, "bold"),
            padding=(18, 11),
            anchor="w",
            borderwidth=0,
        )
        style.map("NavSel.TButton", background=[("active", C["accent"])])

        style.configure(
            "TCheckbutton", background=C["bg"], foreground=C["fg"]
        )
        style.map(
            "TCheckbutton",
            background=[("active", C["bg"])],
            foreground=[("disabled", C["subtle"])],
        )
        style.configure(
            "Card.TCheckbutton", background=C["panel"], foreground=C["fg"]
        )
        style.map(
            "Card.TCheckbutton",
            background=[("active", C["panel"])],
            foreground=[("disabled", C["subtle"])],
        )

        style.configure(
            "TEntry",
            fieldbackground=C["entry_bg"],
            foreground=C["fg"],
            insertcolor=C["fg"],
            bordercolor=C["border"],
        )
        style.configure(
            "Treeview",
            background=C["panel"],
            fieldbackground=C["panel"],
            foreground=C["fg"],
            bordercolor=C["border"],
            rowheight=26,
        )
        style.configure(
            "Treeview.Heading",
            background=C["panel_alt"],
            foreground=C["fg"],
            padding=(6, 6),
        )
        style.map("Treeview", background=[("selected", C["accent"])])

        style.configure("Vertical.TScrollbar", background=C["panel_alt"], troughcolor=C["bg"])
        style.configure("Horizontal.TScrollbar", background=C["panel_alt"], troughcolor=C["bg"])

    def _build_layout(self):
        # 左侧导航栏
        sidebar = ttk.Frame(self, style="Sidebar.TFrame", width=210)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ttk.Label(sidebar, text="Open-LLM-VTuber", style="SidebarTitle.TLabel").pack(
            anchor="w", padx=18, pady=(18, 2)
        )
        ttk.Label(
            sidebar,
            text=f"启动器 v{APP_VERSION} · 项目 v{project_version()}",
            style="SidebarSub.TLabel",
        ).pack(anchor="w", padx=18, pady=(0, 18))

        nav_items = [
            ("home", "一键启动"),
            ("advanced", "高级选项"),
            ("version", "版本管理"),
            ("trouble", "疑难解答"),
            ("about", "关于"),
        ]
        self.nav_btns = {}
        for key, label in nav_items:
            btn = ttk.Button(
                sidebar,
                text=f"  {label}",
                style="Nav.TButton",
                command=lambda k=key: self.show_page(k),
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_btns[key] = btn

        status = ttk.Frame(sidebar, style="Sidebar.TFrame")
        status.pack(side="bottom", fill="x", padx=18, pady=16)
        self.status_dot = tk.Label(
            status, text="●", bg=C["sidebar"], fg=C["subtle"], font=(FONT_UI, 12)
        )
        self.status_dot.pack(side="left")
        self.status_text = ttk.Label(status, text="  未运行", style="SidebarSub.TLabel")
        self.status_text.pack(side="left")

        # 右侧页面容器
        container = ttk.Frame(self)
        container.pack(side="left", fill="both", expand=True)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self.pages = {
            "home": HomePage(self, container),
            "advanced": AdvancedPage(self, container),
            "version": VersionPage(self, container),
            "trouble": TroubleshootPage(self, container),
            "about": AboutPage(self, container),
        }
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

        self.current_page = None

    # ---- 页面与状态管理 ----

    def show_page(self, key: str):
        page = self.pages[key]
        page.tkraise()
        self.current_page = key
        for name, btn in self.nav_btns.items():
            btn.config(style="NavSel.TButton" if name == key else "Nav.TButton")
        if hasattr(page, "on_show"):
            page.on_show()

    def toggle_server(self):
        if self.server.running:
            self.server.stop()
        else:
            self.server.start(
                verbose=self.opt_verbose.get(),
                hf_mirror=self.opt_hf_mirror.get(),
                open_browser=self.opt_open_browser.get(),
            )

    def save_settings(self):
        save_settings(
            {
                "verbose": self.opt_verbose.get(),
                "hf_mirror": self.opt_hf_mirror.get(),
                "open_browser": self.opt_open_browser.get(),
                "autoscroll": self.opt_autoscroll.get(),
            }
        )

    def set_running(self, running: bool):
        self.status_dot.config(fg=C["ok"] if running else C["subtle"])
        self.status_text.config(text="  运行中" if running else "  未运行")
        self.pages["home"].set_running(running)

    # ---- 事件循环 ----

    def _poll_events(self):
        try:
            for _ in range(300):
                kind, payload = self.events.get_nowait()
                if kind == "log":
                    self.pages["home"].log(payload)
                elif kind == "state":
                    self.set_running(payload == "running")
                elif kind == "gitinfo":
                    self.pages["version"].apply_info(payload)
                elif kind == "scan":
                    self.pages["trouble"].add_scan_row(*payload)
                elif kind == "scan_done":
                    pass
        except queue.Empty:
            pass
        self.after(100, self._poll_events)

    def _on_callback_error(self, exc, val, tb):
        import traceback

        msg = "".join(traceback.format_exception(exc, val, tb))
        try:
            messagebox.showerror("启动器内部错误", msg, parent=self)
        except tk.TclError:
            pass

    def _on_close(self):
        if self.server.running:
            if not messagebox.askyesno(
                "确认退出", "服务器仍在运行，退出启动器将同时终止服务器。\n确定退出吗？"
            ):
                return
            self.server.stop()
            time.sleep(0.5)
        self.destroy()


def main():
    app = LauncherApp()
    app.mainloop()


if __name__ == "__main__":
    main()
