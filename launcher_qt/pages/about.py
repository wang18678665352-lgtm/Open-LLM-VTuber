"""页面：关于。"""

from __future__ import annotations

import webbrowser

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from .. import APP_VERSION, DOCS_URL, GITHUB_URL
from ..core.system import project_version
from ..core.theme import color
from ..widgets.common import (
    apply_shadow,
    button,
    card,
    card_layout,
    hint,
    label,
    logo_pixmap,
    page_header,
    pixmap,
)

FEATURES = (
    ("play", "一键启停本地服务"),
    ("terminal", "实时着色的控制台"),
    ("settings", "图形化修改配置"),
    ("branch", "查看版本与更新"),
    ("scan", "一键环境自检"),
    ("package", "可打包单文件 exe"),
)


class AboutPage(QWidget):
    def __init__(self, window) -> None:
        super().__init__()
        self.window = window

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 16)
        layout.setSpacing(14)
        layout.addWidget(page_header("关于", "Open-LLM-VTuber 启动器"))

        # ---- 品牌区 ----
        hero = card(object_name="hero", margins=(24, 22, 24, 22))
        apply_shadow(hero, blur=28, dy=2, alpha=26)
        hero_layout = card_layout(hero)
        hero_layout.setSpacing(14)

        brand = QHBoxLayout()
        brand.setSpacing(16)
        logo = QLabel()
        logo.setFixedSize(64, 64)
        logo.setPixmap(logo_pixmap(64))
        brand.addWidget(logo)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(4)
        name = label("Open-LLM-VTuber 启动器", "cardTitle")
        name.setStyleSheet("font-size: 16pt;")
        brand_text.addWidget(name)
        brand_text.addWidget(
            label(f"启动器 v{APP_VERSION}　·　项目 v{project_version()}", "cardHint")
        )
        brand_text.addWidget(label("简约风格的本地服务图形化启动工具", "cardHint"))
        brand.addLayout(brand_text)
        brand.addStretch(1)
        hero_layout.addLayout(brand)

        features = QGridLayout()
        features.setHorizontalSpacing(18)
        features.setVerticalSpacing(8)
        for index, (icon_name, text) in enumerate(FEATURES):
            item = QWidget()
            item_layout = QHBoxLayout(item)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(8)
            glyph = QLabel()
            glyph.setFixedSize(18, 18)
            glyph.setPixmap(pixmap(icon_name, 18, color("launcher")))
            item_layout.addWidget(glyph)
            item_layout.addWidget(label(text, "cardLabel"))
            item_layout.addStretch(1)
            features.addWidget(item, index // 3, index % 3)
        for column in range(3):
            features.setColumnStretch(column, 1)
        hero_layout.addLayout(features)
        layout.addWidget(hero)

        # ---- 说明 ----
        note_card = card(margins=(20, 18, 20, 18))
        note_layout = card_layout(note_card)
        note_layout.setSpacing(10)
        note_layout.addWidget(label("说明", "cardTitle"))
        note_layout.addWidget(
            label(
                "本版本使用 Qt6（PySide6）原生窗口与原生控件重写，图标全部为矢量绘制，"
                "可打包为单文件 exe，无需额外安装 Python 运行环境。",
                "cardLabel",
            )
        )
        material_note = hint(
            "界面采用简约的 Google Material 浅色风格（主色 #1a73e8），"
            "导航与按钮图标均为运行时绘制的矢量图形，不依赖位图素材。"
            "本启动器为社区自制工具，与 Open-LLM-VTuber 官方无关。",
            card_scoped=True,
        )
        material_note.setWordWrap(True)
        note_layout.addWidget(material_note)

        links = QHBoxLayout()
        links.setSpacing(10)
        links.addWidget(
            button(
                "GitHub 仓库",
                on_click=lambda: webbrowser.open(GITHUB_URL),
                icon_name="code",
                icon_size=17,
            )
        )
        links.addWidget(
            button(
                "官方文档",
                on_click=lambda: webbrowser.open(DOCS_URL),
                icon_name="book",
                icon_size=17,
            )
        )
        links.addStretch(1)
        note_layout.addLayout(links)
        layout.addWidget(note_card)

        layout.addWidget(
            hint(
                "本启动器不会修改项目源码；所有写操作仅限 conf.yaml 与 launcher_settings.json。"
            )
        )
        layout.addStretch(1)
