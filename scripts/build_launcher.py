"""把 Qt6 启动器打包成单文件 exe（PyInstaller）。

用法::

    # 在项目根目录，用启动器的构建环境执行
    .venv-launcher\\Scripts\\python.exe scripts\\build_launcher.py

    # 常用参数
    --onedir        打包成目录（启动更快，体积略大）
    --clean         打包前清理 build/ 与 dist/
    --no-verify     构建完成后不做离屏自检
    --console       保留控制台窗口（排错时用）

产物：dist/Open-LLM-VTuber-Launcher.exe
把 exe 放到项目根目录即可直接使用（它会在自身所在目录向上查找 run_server.py）。
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT / "launcher_qt" / "assets"
ICON_PATH = ASSETS_DIR / "app.ico"
FAVICON_PATH = ROOT / "frontend" / "favicon.ico"
APP_NAME = "Open-LLM-VTuber-Launcher"
ENTRY = ROOT / "run_launcher.py"

# 精简体积：启动器用不到的 Qt 模块（QtCore/QtGui/QtWidgets/QtNetwork 必须保留）
EXCLUDES = (
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtBluetooth",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtDesigner",
    "PySide6.QtGraphs",
    "PySide6.QtHelp",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNfc",
    "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio",
    "PySide6.QtSql",
    "PySide6.QtStateMachine",
    "PySide6.QtTest",
    "PySide6.QtTextToSpeech",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
    "tkinter",
)


def ensure_icon() -> None:
    """launcher_qt/assets/app.ico 缺失时从 frontend/favicon.ico 生成多尺寸图标。"""
    if ICON_PATH.exists():
        return
    if not FAVICON_PATH.exists():
        print(f"[警告] 未找到图标来源 {FAVICON_PATH}，将使用 PyInstaller 默认图标。")
        return
    try:
        from PIL import Image
    except ImportError:
        print("[警告] 未安装 Pillow，跳过图标生成（可先安装：pip install pillow）。")
        return
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    source = Image.open(FAVICON_PATH).convert("RGBA")
    source.save(
        ICON_PATH,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"[图标] 已生成 {ICON_PATH.relative_to(ROOT)}")


def check_prerequisites() -> bool:
    missing: list[str] = []
    for module, hint in (("PyInstaller", "pyinstaller"), ("PySide6", "pyside6-essentials")):
        try:
            __import__(module)
        except ImportError:
            missing.append(hint)
    if missing:
        print("[错误] 构建环境缺少依赖：" + "、".join(missing))
        print("       请先执行：")
        print(
            r"       uv pip install --python .venv-launcher\Scripts\python.exe "
            "pyside6-essentials pyinstaller pillow"
        )
        return False
    return True


def build_command(args: argparse.Namespace) -> list[str]:
    separator = ";" if os.name == "nt" else ":"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        APP_NAME,
        "--distpath",
        str(ROOT / "dist"),
        "--workpath",
        str(ROOT / "build" / "launcher"),
        "--specpath",
        str(ROOT / "build"),
        "--paths",
        str(ROOT),
        "--add-data",
        f"{ASSETS_DIR}{separator}launcher_qt/assets",
        # conf_set() 内部动态导入 ruamel.yaml，PyInstaller 静态分析看不到
        "--collect-all",
        "ruamel.yaml",
        "--hidden-import",
        "ruamel.yaml",
        "--collect-submodules",
        "launcher_qt",
    ]
    command.append("--onedir" if args.onedir else "--onefile")
    command.append("--console" if args.console else "--windowed")
    if ICON_PATH.exists():
        command += ["--icon", str(ICON_PATH)]
    for module in EXCLUDES:
        command += ["--exclude-module", module]
    command.append(str(ENTRY))
    return command


def verify(exe: Path) -> bool:
    """离屏渲染各页面，确认打包产物能独立运行。"""
    out_dir = ROOT / "build" / "verify-shots"
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)
    env = dict(
        os.environ,
        QT_QPA_PLATFORM="offscreen",
        PYTHONIOENCODING="utf-8",
        PYTHONUTF8="1",
    )
    print(f"\n[自检] {exe.name} --screenshot {out_dir.relative_to(ROOT)}")
    try:
        proc = subprocess.run(
            [str(exe), "--screenshot", str(out_dir)],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        print("[自检] 超时（300s），请手动运行 exe 检查。")
        return False
    for line in ((proc.stdout or "") + (proc.stderr or "")).splitlines():
        if "fontconfig" in line or "dejavu" in line or "QFontDatabase" in line:
            continue
        print("       " + line)
    shots = sorted(path.name for path in out_dir.glob("*.png")) if out_dir.exists() else []
    print(f"[自检] 退出码 {proc.returncode}，生成截图 {len(shots)} 张：{', '.join(shots)}")
    return proc.returncode == 0 and len(shots) >= 5


def main() -> int:
    parser = argparse.ArgumentParser(description="打包 Open-LLM-VTuber Qt6 启动器")
    parser.add_argument("--onedir", action="store_true", help="打包成目录而不是单文件")
    parser.add_argument("--clean", action="store_true", help="构建前清理 build/ 与 dist/")
    parser.add_argument("--console", action="store_true", help="保留控制台窗口")
    parser.add_argument("--no-verify", action="store_true", help="跳过构建后的离屏自检")
    args = parser.parse_args()

    os.chdir(ROOT)
    if args.clean:
        for path in (ROOT / "build", ROOT / "dist"):
            if path.exists():
                shutil.rmtree(path, ignore_errors=True)
                print(f"[清理] 已删除 {path.relative_to(ROOT)}")

    if not check_prerequisites():
        return 1
    ensure_icon()

    command = build_command(args)
    print("[构建] " + " ".join(command) + "\n")
    result = subprocess.run(command, cwd=str(ROOT))
    if result.returncode != 0:
        print(f"\n[失败] PyInstaller 退出码 {result.returncode}")
        return result.returncode

    exe = ROOT / "dist" / (APP_NAME + ("" if args.onedir else ".exe"))
    if args.onedir:
        exe = ROOT / "dist" / APP_NAME / (APP_NAME + ".exe")
    if not exe.exists():
        print(f"\n[失败] 未找到构建产物：{exe}")
        return 1

    size_mb = exe.stat().st_size / (1024 * 1024)
    print(f"\n[完成] {exe}  ({size_mb:.1f} MB)")
    print("[提示] 把该 exe 放到项目根目录（与 run_server.py 同级）即可直接双击使用。")

    if not args.no_verify and not verify(exe):
        print("[自检] 未通过，请用 --console 重新打包以查看报错。")
        return 1
    if not args.no_verify:
        print("[自检] 通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
