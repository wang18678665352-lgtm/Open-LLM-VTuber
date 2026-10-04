"""生成启动器多尺寸图标（launcher_qt/assets/app.ico）。

图标沿用项目原有的 ``frontend/favicon.ico``：把源图按
16 / 24 / 32 / 48 / 64 / 128 / 256 七个尺寸分别重采样后写入一个 ICO 容器，
Windows 会为标题栏、任务栏、资源管理器各自挑选最合适的一档，不会出现
“把小尺寸位图放大”的模糊。

用法：
    .venv-launcher\\Scripts\\python.exe scripts\\make_icon.py
    .venv-launcher\\Scripts\\python.exe scripts\\make_icon.py --force
    .venv-launcher\\Scripts\\python.exe scripts\\make_icon.py --source path\\to\\icon.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "frontend" / "favicon.ico"
DEFAULT_OUTPUT = ROOT / "launcher_qt" / "assets" / "app.ico"
DEFAULT_SIZES = (16, 24, 32, 48, 64, 128, 256)


def _display(path: Path) -> str:
    """尽量显示相对项目根的路径（不在项目内时显示绝对路径）。"""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def build(source: Path, output: Path, sizes: tuple[int, ...]) -> None:
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - 构建环境已装 Pillow
        print("[错误] 需要 Pillow，请先安装：pip install pillow")
        raise SystemExit(2)

    if not source.exists():
        print(f"[错误] 找不到图标来源 {source}")
        raise SystemExit(2)

    image = Image.open(source).convert("RGBA")
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="ICO", sizes=[(size, size) for size in sizes])
    print(
        f"[图标] 已生成 {_display(output)} "
        f"（来源 {_display(source)}，{len(sizes)} 个尺寸："
        f"{', '.join(str(s) for s in sizes)}，{output.stat().st_size} 字节）"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成启动器图标 app.ico")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--sizes",
        default=",".join(str(size) for size in DEFAULT_SIZES),
        help="逗号分隔的尺寸列表",
    )
    parser.add_argument("--force", action="store_true", help="已存在时也重新生成")
    args = parser.parse_args(argv)

    source = args.source if args.source.is_absolute() else (ROOT / args.source)
    output = args.output if args.output.is_absolute() else (ROOT / args.output)

    if output.exists() and not args.force:
        print(f"[跳过] {_display(output)} 已存在（加 --force 可重新生成）")
        return 0

    sizes = tuple(int(part) for part in args.sizes.split(",") if part.strip())
    build(source, output, sizes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
