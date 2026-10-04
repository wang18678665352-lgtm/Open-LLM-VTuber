"""生成启动器多尺寸图标（launcher_qt/assets/app.ico）。

图标不再来自 frontend/favicon.ico 位图，而是用与界面同一套矢量绘制代码
（``launcher_qt.core.icons.logo_pixmap``）在离屏平台上按每个尺寸单独渲染，
因此 16px 到 256px 都保持锐利。

用法：
    .venv-launcher\\Scripts\\python.exe scripts\\make_icon.py
    .venv-launcher\\Scripts\\python.exe scripts\\make_icon.py --force
"""

from __future__ import annotations

import argparse
import os
import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "launcher_qt" / "assets" / "app.ico"
DEFAULT_SIZES = (16, 24, 32, 48, 64, 128, 256)


def render_png(size: int) -> bytes:
    """把矢量标记渲染成 PNG 字节。"""
    from PySide6.QtCore import QBuffer, QByteArray

    from launcher_qt.core.icons import logo_pixmap

    pixmap = logo_pixmap(size)
    if pixmap is None or pixmap.isNull():
        raise RuntimeError("矢量标记渲染失败")

    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QBuffer.OpenModeFlag.WriteOnly)
    pixmap.save(buffer, "PNG")
    buffer.close()
    return bytes(data)


def write_ico(images: list[tuple[int, bytes]], output: Path) -> None:
    """把若干 (尺寸, PNG 字节) 写成 ICO 容器（Vista+ 支持 PNG 负载）。"""
    count = len(images)
    header = struct.pack("<HHH", 0, 1, count)
    offset = 6 + 16 * count

    entries = bytearray()
    payload = bytearray()
    for size, data in images:
        dimension = 0 if size >= 256 else size
        entries += struct.pack(
            "<BBBBHHII",
            dimension,
            dimension,
            0,
            0,
            1,
            32,
            len(data),
            offset,
        )
        payload += data
        offset += len(data)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(header + bytes(entries) + bytes(payload))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成启动器图标 app.ico")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--sizes",
        default=",".join(str(size) for size in DEFAULT_SIZES),
        help="逗号分隔的尺寸列表",
    )
    parser.add_argument("--force", action="store_true", help="已存在时也重新生成")
    args = parser.parse_args(argv)

    if args.output.exists() and not args.force:
        print(f"[跳过] {args.output.relative_to(ROOT)} 已存在（加 --force 可重新生成）")
        return 0

    sizes = tuple(int(part) for part in args.sizes.split(",") if part.strip())
    # 离屏渲染：不弹窗口，也不需要真实显示器
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    sys.path.insert(0, str(ROOT))

    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication([sys.argv[0]])
    del app  # 仅为初始化 Qt 平台插件

    with tempfile.TemporaryDirectory() as tmp:
        cache: dict[int, bytes] = {}
        for size in sizes:
            cache[size] = render_png(size)
        # ICO 尺寸按从小到大写入，Windows 会挑选最接近的一档
        write_ico([(size, cache[size]) for size in sorted(cache)], args.output)

    print(
        f"[图标] 已生成 {args.output.relative_to(ROOT)} "
        f"（{len(sizes)} 个尺寸：{', '.join(str(s) for s in sorted(sizes))}，"
        f"{args.output.stat().st_size} 字节）"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
