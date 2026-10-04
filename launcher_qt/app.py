"""主窗口：侧边栏导航 + 页面堆栈 + 系统托盘 + 单实例。"""

from __future__ import annotations

from PySide6.QtCore import (
    QAbstractAnimation,
    QEasingCurve,
    QEvent,
    QObject,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from . import APP_NAME, APP_VERSION
from .core.config import SETTINGS_DEFAULTS, load_settings, save_settings
from .core.icons import apply_icon
from .core.paths import ICON_PATH
from .core.server import ServerController
from .core.system import project_version
from .core.theme import PALETTE, apply_native_chrome
from .pages.about import AboutPage
from .pages.advanced import AdvancedPage
from .pages.home import HomePage
from .pages.models import ModelsPage
from .pages.troubleshoot import TroubleshootPage
from .pages.version import VersionPage
from .widgets.common import apply_shadow, logo_pixmap

SINGLE_INSTANCE_KEY = "Open-LLM-VTuber-Launcher-1"

#: 运行中状态点的呼吸色（比 PALETTE["ok"] 暗一档）
PULSE_DIM = "#2f7d5c"

#: (页面 key, 导航标题, 页面类, 导航图标)
PAGES: tuple[tuple[str, str, type, str], ...] = (
    ("home", "一键启动", HomePage, "play"),
    ("models", "模型配置", ModelsPage, "robot"),
    ("advanced", "高级选项", AdvancedPage, "settings"),
    ("version", "版本管理", VersionPage, "branch"),
    ("troubleshoot", "疑难解答", TroubleshootPage, "scan"),
    ("about", "关于", AboutPage, "info"),
)


class SingleInstanceGuard(QObject):
    """用本地套接字保证同一时间只有一个启动器实例。"""

    activated = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.server: QLocalServer | None = None

    def acquire(self) -> bool:
        """返回 True 表示本进程成为唯一实例，False 表示已有实例在运行。"""
        probe = QLocalSocket()
        probe.connectToServer(SINGLE_INSTANCE_KEY)
        if probe.waitForConnected(400):
            probe.write(b"activate")
            probe.flush()
            probe.waitForBytesWritten(400)
            probe.disconnectFromServer()
            return False
        QLocalServer.removeServer(SINGLE_INSTANCE_KEY)
        self.server = QLocalServer(self)
        self.server.newConnection.connect(self._on_new_connection)
        return bool(self.server.listen(SINGLE_INSTANCE_KEY))

    def _on_new_connection(self) -> None:
        if self.server is None:
            return
        connection = self.server.nextPendingConnection()
        if connection is not None:
            connection.readAll()
            connection.disconnectFromServer()
            connection.deleteLater()
        self.activated.emit()


class LauncherWindow(QMainWindow):
    def __init__(self, root=None) -> None:
        super().__init__(None)
        self.root = root
        self.options: dict[str, object] = dict(SETTINGS_DEFAULTS)
        self.options.update(load_settings() or {})
        self._force_quit = False
        self._chrome_applied = False
        self.tray: QSystemTrayIcon | None = None
        self._current_page = ""
        self._fade_anim: QPropertyAnimation | None = None
        self._pulse_on = False
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(700)
        self._pulse_timer.timeout.connect(self._pulse_tick)

        self.setWindowTitle(APP_NAME)
        self.resize(1120, 740)
        self.setMinimumSize(980, 660)
        if ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(ICON_PATH)))

        self.server = ServerController(self)
        self.pages: dict[str, QWidget] = {}
        self.nav_buttons: dict[str, QPushButton] = {}

        self._build_ui()
        self._build_tray()

        self.server.logLine.connect(self.pages["home"].log)
        self.server.stateChanged.connect(self._on_server_state)
        self.show_page("home")

    # ------------------------------------------------------------------
    # 界面搭建
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("content")
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        for key, _title, factory, _icon in PAGES:
            page = factory(self)
            self.pages[key] = page
            self.stack.addWidget(page)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(6)

        # ---- 品牌区：图标 + 名称 + 版本 ----
        brand = QHBoxLayout()
        brand.setSpacing(10)
        logo = QLabel()
        logo.setFixedSize(38, 38)
        pixmap = logo_pixmap(38)
        if pixmap is not None:
            logo.setPixmap(pixmap)
        brand.addWidget(logo)

        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        title = QLabel("Open-LLM-VTuber")
        title.setObjectName("sidebarTitle")
        subtitle = QLabel(f"启动器 v{APP_VERSION} · 项目 v{project_version()}")
        subtitle.setObjectName("sidebarSub")
        brand_text.addWidget(title)
        brand_text.addWidget(subtitle)
        brand.addLayout(brand_text)
        brand.addStretch(1)
        layout.addLayout(brand)
        layout.addSpacing(16)

        # ---- 导航 ----
        group = QButtonGroup(self)
        group.setExclusive(True)
        for key, text, _factory, icon_name in PAGES:
            nav = QPushButton(text)
            nav.setObjectName("navButton")
            nav.setCheckable(True)
            nav.setCursor(Qt.CursorShape.PointingHandCursor)
            nav.setIconSize(QSize(18, 18))
            apply_icon(nav, icon_name, color=PALETTE["subtle"], size=18)
            nav.clicked.connect(lambda _checked=False, name=key: self.show_page(name))
            group.addButton(nav)
            self.nav_buttons[key] = nav
            layout.addWidget(nav)

        layout.addStretch(1)

        # ---- 底部状态药丸 ----
        chip = QFrame()
        chip.setObjectName("statusChip")
        chip_layout = QHBoxLayout(chip)
        chip_layout.setContentsMargins(10, 8, 10, 8)
        chip_layout.setSpacing(8)
        self.status_dot = QLabel()
        self.status_dot.setObjectName("statusDot")
        self.status_text = QLabel("未运行")
        self.status_text.setObjectName("statusText")
        chip_layout.addWidget(self.status_dot)
        chip_layout.addWidget(self.status_text)
        chip_layout.addStretch(1)
        apply_shadow(chip, blur=24, dy=6, alpha=70)
        layout.addWidget(chip)
        return sidebar

    def _build_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        if ICON_PATH.exists():
            icon = QIcon(str(ICON_PATH))
        else:
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self.tray = QSystemTrayIcon(icon, self)

        menu = QMenu(self)
        self.tray_show_action = QAction("显示主窗口", self)
        self.tray_show_action.triggered.connect(self.restore_window)
        self.tray_toggle_action = QAction("一键启动", self)
        self.tray_toggle_action.triggered.connect(self.toggle_server)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_app)
        menu.addAction(self.tray_show_action)
        menu.addAction(self.tray_toggle_action)
        menu.addSeparator()
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.setToolTip(APP_NAME)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    # ------------------------------------------------------------------
    # 页面与状态
    # ------------------------------------------------------------------
    def show_page(self, key: str) -> None:
        page = self.pages.get(key)
        if page is None:
            return
        changed = key != self._current_page
        self._current_page = key
        self.stack.setCurrentWidget(page)
        button = self.nav_buttons.get(key)
        if button is not None:
            button.setChecked(True)
        self._refresh_nav_icons(key)
        on_show = getattr(page, "on_show", None)
        if callable(on_show):
            on_show()
        if changed:
            self._fade_in(page)

    def _fade_in(self, page: QWidget) -> None:
        """切换页面时做一次轻微的淡入，让界面不显得生硬。"""
        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(170)
        anim.setStartValue(0.3)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def _cleanup() -> None:
            page.setGraphicsEffect(None)

        anim.finished.connect(_cleanup)
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        self._fade_anim = anim

    def _refresh_nav_icons(self, active: str) -> None:
        """选中项用高亮色图标，其余用弱化色。"""
        for key, _text, _factory, icon_name in PAGES:
            nav = self.nav_buttons.get(key)
            if nav is None:
                continue
            color = "#ffffff" if key == active else PALETTE["subtle"]
            apply_icon(nav, icon_name, color=color, size=18)
            nav.setIconSize(QSize(18, 18))

    def set_option(self, name: str, checked: bool) -> None:
        self.options[name] = bool(checked)
        self.save_options()

    def save_options(self) -> None:
        save_settings(self.options)

    def toggle_server(self) -> None:
        if self.server.running:
            self.server.stop()
            return
        self.server.start(
            verbose=bool(self.options.get("verbose", False)),
            hf_mirror=bool(self.options.get("hf_mirror", False)),
            open_browser=bool(self.options.get("open_browser", True)),
        )

    def _dot_style(self, color: str) -> str:
        return (
            "border-radius: 4px; min-width: 8px; max-width: 8px;"
            " min-height: 8px; max-height: 8px; background: " + color + ";"
        )

    def _pulse_tick(self) -> None:
        self._pulse_on = not self._pulse_on
        self.status_dot.setStyleSheet(
            self._dot_style(PALETTE["ok"] if self._pulse_on else PULSE_DIM)
        )

    def _on_server_state(self, running: bool) -> None:
        home = self.pages.get("home")
        if home is not None and hasattr(home, "set_running"):
            home.set_running(running)
        if running:
            self._pulse_on = True
            self.status_dot.setStyleSheet(self._dot_style(PALETTE["ok"]))
            self._pulse_timer.start()
        else:
            self._pulse_timer.stop()
            self.status_dot.setStyleSheet(self._dot_style(PALETTE["subtle"]))
        self.status_text.setText("运行中" if running else "未运行")
        self.status_text.setStyleSheet(
            f"color: {PALETTE['ok'] if running else PALETTE['subtle']};"
        )
        if self.tray is not None:
            self.tray_toggle_action.setText("终止运行" if running else "一键启动")
            self.tray.setToolTip(f"{APP_NAME} · {'运行中' if running else '未运行'}")

    # ------------------------------------------------------------------
    # 托盘 / 窗口行为
    # ------------------------------------------------------------------
    def _on_tray_activated(self, reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.restore_window()

    def restore_window(self) -> None:
        if self.isMinimized() or not self.isVisible():
            self.setWindowState(
                (self.windowState() & ~Qt.WindowState.WindowMinimized)
                | Qt.WindowState.WindowActive
            )
            self.show()
        self.raise_()
        self.activateWindow()

    def quit_app(self) -> None:
        self._force_quit = True
        self.close()

    def changeEvent(self, event) -> None:  # noqa: N802
        if (
            event.type() == QEvent.Type.WindowStateChange
            and self.isMinimized()
            and self.tray is not None
            and self.options.get("minimize_to_tray")
        ):
            self.hide()
            self.tray.showMessage(
                APP_NAME,
                "启动器已最小化到系统托盘，双击图标可重新打开。",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )
        super().changeEvent(event)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._chrome_applied:
            self._chrome_applied = True
            apply_native_chrome(self, dark=True)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._force_quit:
            if self.server.running:
                self.server.stop()
            event.accept()
            return
        if self.tray is not None and self.options.get("minimize_to_tray"):
            event.ignore()
            self.hide()
            self.tray.showMessage(
                APP_NAME,
                "启动器已最小化到系统托盘，双击图标可重新打开。",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )
            return
        if self.server.running:
            answer = QMessageBox.question(
                self,
                "确认退出",
                "服务器仍在运行，退出启动器将同时终止服务器。",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.server.stop()
        event.accept()
