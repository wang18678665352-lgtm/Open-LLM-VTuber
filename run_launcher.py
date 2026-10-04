"""Qt6 启动器入口脚本（供 PyInstaller 打包与直接运行使用）。

    python run_launcher.py            # 启动图形界面
    python -m launcher_qt             # 等价的模块方式（开发用）

打包见 ``scripts/build_launcher.py``。
"""

from __future__ import annotations

from launcher_qt.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
