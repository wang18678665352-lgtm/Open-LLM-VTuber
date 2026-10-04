"""环境探测：版本信息、git 状态、一键扫描与系统工具调用。"""

from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path

from .config import conf_get
from .paths import CONF_PATH, CREATE_NO_WINDOW, IS_FROZEN, IS_WIN, ROOT, VENV_PY

def run_quiet(cmd, timeout: int = 30) -> tuple[int, str]:
    """静默执行命令，返回 ``(returncode, 合并输出)``。"""
    try:
        proc = subprocess.run(
            [str(part) for part in cmd],
            cwd=str(ROOT),
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


def open_path(path) -> None:
    """用系统默认程序打开文件或目录（Windows 走 ShellExecute）。"""
    target = str(path)
    try:
        if IS_WIN:
            os.startfile(target)  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])
    except OSError:
        pass


def project_python() -> list[str] | None:
    """返回可直接执行 ``run_server.py``/``upgrade.py`` 的命令前缀。"""
    if VENV_PY.exists():
        return [str(VENV_PY)]
    uv = shutil.which("uv")
    if uv:
        return [uv, "run", "python"]
    if not IS_FROZEN:
        return [sys.executable]
    return None


def dependency_install_tasks() -> list[dict]:
    """安装/修复依赖的任务序列（优先 uv，退化到 pip）。"""
    uv = shutil.which("uv")
    if uv:
        return [{"cmd": [uv, "sync"]}]
    python = project_python()
    if not python:
        return []
    return [{"cmd": [*python, "-m", "pip", "install", "-r", "requirements.txt"]}]


def env_info_lines() -> list[str]:
    """「高级选项」页的环境信息面板内容。"""
    lines: list[str] = []

    def add(key: str, value: str) -> None:
        lines.append(f"{key:<14}{value}")

    if IS_FROZEN:
        add("启动器", f"{sys.executable}（打包版 exe）")
    else:
        add("启动器 Python", f"{sys.executable} ({sys.version.split()[0]})")
    if VENV_PY.exists():
        code, out = run_quiet([str(VENV_PY), "--version"])
        add("项目 Python", f"{VENV_PY} ({out.strip() if code == 0 else '异常'})")
    else:
        add("项目 Python", ".venv 不存在，请先在「疑难解答」页安装依赖")
    uv = shutil.which("uv")
    if uv:
        code, out = run_quiet([uv, "--version"])
        add("uv", out.strip() if code == 0 else uv)
    else:
        add("uv", "未安装（https://docs.astral.sh/uv/）")
    add("项目版本", f"v{project_version()}")
    add("配置文件版本", conf_get("conf_version", "未知"))
    add("前端地址", f"http://127.0.0.1:{conf_get('port', '12393')}")
    add("项目目录", str(ROOT))
    return lines


def collect_git_info() -> dict[str, str]:
    """版本管理页需要的一组 git 信息。"""
    info = {
        "version": f"v{project_version()}",
        "conf": conf_get("conf_version", "未知"),
    }
    code, branch = run_quiet(["git", "branch", "--show-current"])
    info["branch"] = (
        branch.strip()
        if code == 0 and branch.strip()
        else "（非 git 仓库或 git 不可用）"
    )
    code, commit = run_quiet(["git", "log", "-1", "--format=%h  %s  (%cr)"])
    info["commit"] = commit.strip() if code == 0 else "未知"
    code, counts = run_quiet(
        ["git", "rev-list", "--left-right", "--count", "HEAD...@{upstream}"]
    )
    if code == 0 and counts.strip():
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
    return info


def scan_environment(emit, is_server_running: bool) -> None:
    """一键扫描：逐项 emit(name, level, detail)，level ∈ {ok, warn, err}。"""

    # 1. 项目虚拟环境 + Python 版本
    if VENV_PY.exists():
        code, out = run_quiet(
            [
                str(VENV_PY),
                "-c",
                "import sys;print('%d.%d.%d' % sys.version_info[:3])",
            ]
        )
        version = out.strip().splitlines()[-1] if out.strip() else "未知"
        try:
            major, minor = version.split(".")[:2]
            version_ok = major == "3" and 10 <= int(minor) <= 12
        except (ValueError, IndexError):
            version_ok = False
        if code == 0 and version_ok:
            emit(
                "Python 版本",
                "ok",
                f".venv 中的 Python {version} 符合要求（>=3.10,<3.13）",
            )
        else:
            emit(
                "Python 版本",
                "err",
                f".venv 中的 Python {version} 不符合要求（需要 >=3.10,<3.13），"
                "建议删除 .venv 后重新安装依赖",
            )
    else:
        emit("Python 虚拟环境", "err", ".venv 不存在，请点击「安装 / 修复依赖」")

    # 2. uv
    uv = shutil.which("uv")
    if uv:
        code, out = run_quiet([uv, "--version"])
        emit(
            "uv 包管理器",
            "ok" if code == 0 else "warn",
            out.strip() if code == 0 else "uv 存在但无法执行",
        )
    else:
        emit("uv 包管理器", "warn", "未安装 uv；安装依赖与更新将退化到 pip，速度较慢")

    # 3. 关键依赖可导入
    if VENV_PY.exists():
        code, out = run_quiet(
            [
                str(VENV_PY),
                "-c",
                "import fastapi, loguru, yaml, uvicorn, openai, sherpa_onnx",
            ],
            timeout=90,
        )
        if code == 0:
            emit(
                "关键依赖",
                "ok",
                "fastapi / loguru / uvicorn / openai / sherpa-onnx 均可导入",
            )
        else:
            tail = out.strip().splitlines()[-1] if out.strip() else ""
            emit("关键依赖", "err", f"依赖缺失或损坏（{tail}），请点击「安装 / 修复依赖」")

    # 4. conf.yaml
    if CONF_PATH.exists():
        emit(
            "配置文件",
            "ok",
            f"conf.yaml 存在（配置版本 {conf_get('conf_version', '未知')}）",
        )
    else:
        emit(
            "配置文件",
            "err",
            "conf.yaml 不存在，请从 config_templates 目录复制一份默认配置到项目根目录",
        )

    # 5. 前端子模块
    if (ROOT / "frontend" / "index.html").exists():
        emit("前端子模块", "ok", "frontend/index.html 存在")
    else:
        emit("前端子模块", "err", "前端文件缺失，请点击「初始化 / 修复前端子模块」")

    # 6. Live2D 模型
    live2d_dir = ROOT / "live2d-models"
    models = (
        [path for path in live2d_dir.iterdir() if path.is_dir()]
        if live2d_dir.exists()
        else []
    )
    if models:
        preview = "、".join(path.name for path in models[:4])
        emit("Live2D 模型", "ok", f"发现 {len(models)} 个模型：{preview}")
    else:
        emit("Live2D 模型", "err", "live2d-models 目录为空，请检查 git 子模块是否完整")

    # 7. ASR 模型
    models_dir = ROOT / "models"
    asr_models = list(models_dir.glob("sherpa-onnx-*")) if models_dir.exists() else []
    if asr_models:
        emit("本地 ASR 模型", "ok", f"已下载：{asr_models[0].name}")
    else:
        emit(
            "本地 ASR 模型",
            "warn",
            "未检测到 sherpa-onnx 模型；若使用本地 ASR，首次启动会自动下载",
        )

    # 8. 端口占用
    port_text = conf_get("port", "12393") or "12393"
    try:
        with socket.create_connection(("127.0.0.1", int(port_text)), timeout=1):
            if is_server_running:
                emit("端口占用", "ok", f"端口 {port_text} 正在被本启动器运行的服务使用")
            else:
                emit(
                    "端口占用",
                    "warn",
                    f"端口 {port_text} 已被其他程序占用，"
                    "请在「高级选项」中修改端口或关闭占用程序",
                )
    except (OSError, ValueError):
        emit("端口占用", "ok", f"端口 {port_text} 空闲")


def frontend_entry_exists() -> bool:
    return (ROOT / "frontend" / "index.html").exists()


def default_config_template() -> Path | None:
    for name in ("conf.ZH.default.yaml", "conf.default.yaml"):
        candidate = ROOT / "config_templates" / name
        if candidate.exists():
            return candidate
    return None
