"""启动器入口。

用法::

    python -m launcher_qt                  # 正常启动图形界面
    python -m launcher_qt --root D:\\path   # 指定项目根目录
    python -m launcher_qt --selftest       # 离屏自检（CI / 打包验证）
    python -m launcher_qt --screenshot DIR # 离屏渲染各页面并保存截图
"""

from __future__ import annotations

import argparse
import os
import sys


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="launcher_qt",
        description="Open-LLM-VTuber 启动器（Qt6 原生版）",
    )
    parser.add_argument("--root", default=None, help="项目根目录（默认自动探测）")
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="离屏启动、构建全部页面并自检后退出",
    )
    parser.add_argument(
        "--screenshot",
        default=None,
        metavar="DIR",
        help="离屏渲染每个页面并保存 PNG 到指定目录",
    )
    return parser.parse_args(argv)


def _describe_environment() -> list[str]:
    from .core.paths import CONF_PATH, ICON_PATH, ROOT, VENV_PY
    from .core.system import project_version

    lines = [
        f"项目根目录 : {ROOT}",
        f"项目版本   : v{project_version()}",
        f"conf.yaml  : {'存在' if CONF_PATH.exists() else '缺失'}",
        f"项目 .venv : {'存在' if VENV_PY.exists() else '缺失'}",
        f"启动器图标 : {'存在' if ICON_PATH.exists() else '缺失（将使用系统默认图标）'}",
        f"运行模式   : {'打包 exe' if getattr(sys, 'frozen', False) else '源码'}",
    ]
    return lines


def _ensure_streams() -> None:
    """保证 print() 在 windowed exe（无控制台）里也不会崩，并统一按 UTF-8 输出。

    PyInstaller 的 ``--windowed`` 产物中 ``sys.stdout`` / ``sys.stderr`` 可能为 None，
    此时把它们接到空设备上，避免任何 print 触发 AttributeError；有句柄（被父进程重定向）
    时则强制 UTF-8，避免中文在 GBK 代码页下变成乱码。
    """
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None:
            devnull = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
            setattr(sys, name, devnull)
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass


def main(argv: list[str] | None = None) -> int:
    _ensure_streams()
    args = parse_args(list(sys.argv[1:] if argv is None else argv))
    if args.root:
        os.environ["LLV_LAUNCHER_ROOT"] = os.path.abspath(args.root)

    from PySide6.QtWidgets import QApplication

    from . import APP_NAME, APP_VERSION
    from .app import LauncherWindow, SingleInstanceGuard
    from .core.icons import logo_icon
    from .core.paths import ICON_PATH
    from .core.theme import build_stylesheet, high_dpi_rounding_policy, set_app_user_model_id

    high_dpi_rounding_policy()
    set_app_user_model_id("Open-LLM-VTuber.Launcher")

    app = QApplication(sys.argv[:1])
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(logo_icon())
    app.setStyleSheet(build_stylesheet())

    headless = bool(args.selftest or args.screenshot)

    guard = None
    if not headless:
        guard = SingleInstanceGuard()
        if not guard.acquire():
            print("[启动器] 已有一个启动器实例在运行，本次启动已退出。")
            return 0

    try:
        window = LauncherWindow(root=args.root)
    except Exception as exc:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        print(f"[启动器] 界面初始化失败: {exc}")
        try:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(
                None,
                "启动器启动失败",
                f"界面初始化失败：\n\n{exc}\n\n请把上面的错误信息反馈给启动器作者。",
            )
        except Exception:  # noqa: BLE001
            pass
        return 1

    if guard is not None:
        guard.activated.connect(window.restore_window)

    window.show()

    if headless:
        return _run_headless(app, window, args)

    return app.exec()


def _settle(app, rounds: int = 12, delay: float = 0.05) -> None:
    import time

    for _ in range(rounds):
        app.processEvents()
        time.sleep(delay)

def _run_headless(app, window, args: argparse.Namespace) -> int:
    for line in _describe_environment():
        print(line)

    keys = list(window.pages.keys())
    print(f"页面数量   : {len(keys)} -> {', '.join(keys)}")
    _settle(app)

    if args.screenshot:
        from pathlib import Path

        out_dir = Path(args.screenshot)
        out_dir.mkdir(parents=True, exist_ok=True)
        for key in keys:
            window.show_page(key)
            _settle(app, rounds=32)
            out_file = out_dir / f"{key}.png"
            if window.grab().save(str(out_file)):
                print(f"截图已保存 : {out_file}")
            else:
                print(f"截图保存失败: {out_file}")
            variants = getattr(window.pages[key], "screenshot_variants", None)
            if callable(variants):
                for name, run in variants():
                    run()
                    _settle(app, rounds=24)
                    extra_file = out_dir / f"{key}-{name}.png"
                    if window.grab().save(str(extra_file)):
                        print(f"截图已保存 : {extra_file}")
        return 0

    if args.selftest:
        for key in keys:
            window.show_page(key)
            _settle(app, rounds=2)
        print("自检完成   : 全部页面构建成功，无异常。")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
