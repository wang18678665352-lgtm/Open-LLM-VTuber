"""项目路径探测（兼容源码运行与 PyInstaller 冻结后的 exe）。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

IS_WIN = os.name == "nt"
CREATE_NO_WINDOW = 0x08000000 if IS_WIN else 0

#: 项目根的识别标志
_ROOT_MARKERS = ("run_server.py", "pyproject.toml")


def _looks_like_root(path: Path) -> bool:
    return any((path / marker).exists() for marker in _ROOT_MARKERS)


def _search_upwards(start: Path, levels: int = 5) -> Path:
    candidates = [start, *list(start.parents)[:levels]]
    for candidate in candidates:
        if _looks_like_root(candidate):
            return candidate
    return start


def detect_root(explicit: str | os.PathLike[str] | None = None) -> Path:
    """定位 Open-LLM-VTuber 项目根目录。

    优先级：命令行/参数 > 环境变量 ``LLV_LAUNCHER_ROOT`` > exe 或源码所在目录向上查找。
    """
    if explicit:
        path = Path(explicit).expanduser()
        if path.is_dir():
            return path.resolve()
    env = os.environ.get("LLV_LAUNCHER_ROOT")
    if env:
        path = Path(env).expanduser()
        if path.is_dir():
            return path.resolve()
    if getattr(sys, "frozen", False):
        start = Path(sys.executable).resolve().parent
    else:
        # launcher_qt/core/paths.py -> launcher_qt/core -> launcher_qt -> 仓库根
        start = Path(__file__).resolve().parents[2]
    return _search_upwards(start)


ROOT = detect_root()

IS_FROZEN = bool(getattr(sys, "frozen", False))

VENV_PY = (
    ROOT / ".venv" / "Scripts" / "python.exe"
    if IS_WIN
    else ROOT / ".venv" / "bin" / "python"
)
CONF_PATH = ROOT / "conf.yaml"
CONF_BAK_PATH = ROOT / "conf.yaml.launcher.bak"
SETTINGS_PATH = ROOT / "launcher_settings.json"

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def asset_path(name: str) -> Path:
    """返回打包进应用的资源文件路径（源码运行与冻结运行都能命中）。"""
    for base in (ASSETS_DIR, Path(__file__).resolve().parent.parent / "assets"):
        candidate = base / name
        if candidate.exists():
            return candidate
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidate = Path(meipass) / "launcher_qt" / "assets" / name
        if candidate.exists():
            return candidate
    return ASSETS_DIR / name


ICON_PATH = asset_path("app.ico")
