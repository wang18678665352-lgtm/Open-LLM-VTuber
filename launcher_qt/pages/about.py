"""页面：关于。"""

from __future__ import annotations

import webbrowser

from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from .. import APP_VERSION, DOCS_URL, GITHUB_URL
from ..core.system import project_version
from ..widgets.common import button, card, card_layout, hint, label, page_title


class AboutPage(QWidget):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)
        layout.addWidget(page_title("关于"))

        about_card = card(margins=(24, 22, 24, 22))
        about_layout = card_layout(about_card)
        about_layout.setSpacing(12)

        title = label("Open-LLM-VTuber 启动器", "cardTitle")
        title.setStyleSheet("font-size: 14pt;")
        about_layout.addWidget(title)

        version = label(
            f"启动器 v{APP_VERSION}    项目 v{project_version()}", "cardHint"
        )
        about_layout.addWidget(version)

        description = label(
            "一个仿秋叶启动器（绘世）风格的图形化启动工具：\n"
            "一键启停服务、实时控制台、配置修改、版本更新与环境自检。\n\n"
            "本版本使用 Qt6（PySide6）原生窗口与原生控件重写，可打包为单文件 exe，\n"
            "无需额外安装 Python 运行环境。\n\n"
            "界面灵感致敬 秋葉aaaki 的绘世启动器。\n"
            "本启动器为社区自制工具，与 Open-LLM-VTuber 官方无关。"
        )
        about_layout.addWidget(description)

        links = QHBoxLayout()
        links.addWidget(
            button("GitHub 仓库", on_click=lambda: webbrowser.open(GITHUB_URL))
        )
        links.addWidget(button("官方文档", on_click=lambda: webbrowser.open(DOCS_URL)))
        links.addStretch(1)
        about_layout.addLayout(links)

        layout.addWidget(about_card)
        layout.addWidget(
            hint(
                "本启动器不会修改项目源码；所有写操作仅限 conf.yaml 与 launcher_settings.json。"
            )
        )
        layout.addStretch(1)
