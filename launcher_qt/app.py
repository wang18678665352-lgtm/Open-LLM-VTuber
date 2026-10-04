"""主窗口：侧边栏导航 + 页面堆栈 + 系统托盘 + 单实例。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt, Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
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
from .core.paths import ICON_PATH
from .core.server import ServerController
from .core.system import project_version
from .core.theme import PALETTE, apply_native_chrome
from .pages.about import AboutPage
from .pages.advanced import AdvancedPage
from .pages.home import HomePage
from .pages.troubleshoot import TroubleshootPage
from .pages.version import VersionPage

SINGLE_INSTANCE_KEY = "Open-LLM-VTuber-Launcher-1"

PAGES: tuple[tuple[str, str, type], ...] = (
    ("home", "一键启动", HomePage),
    ("advanced", "高级选项", AdvancedPage),
    ("version", "版本管理", VersionPage),
    ("troubleshoot", "疑难解答", TroubleshootPage),
    ("about", "关于", AboutPage),
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

        self.setWindowTitle(APP_NAME)
        self.resize(1040, 680)
        self.setMinimumSize(920, 600)
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
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_sidebar())

        self.stack = QStackedWidget()
        for key, _title, factory in PAGES:
            page = factory(self)
            self.pages[key] = page
            self.stack.addWidget(page)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(central)

    def _build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 20, 16, 14)
        layout.setSpacing(6)

        title = QLabel("Open-LLM-VTuber")
        title.setObjectName("sidebarTitle")
        layout.addWidget(title)

        subtitle = QLabel(f"启动器 v{APP_VERSION}\n项目 v{project_version()}")
        subtitle.setObjectName("sidebarSub")
        layout.addWidget(subtitle)
        layout.addSpacing(18)

        group = QButtonGroup(self)
        group.setExclusive(True)
        for key, text, _factory in PAGES:
            nav = QPushButton(text)
            nav.setObjectName("navButton")
            nav.setCheckable(True)
            nav.setCursor(Qt.CursorShape.PointingHandCursor)
            nav.clicked.connect(lambda _checked=False, name=key: self.show_page(name))
            group.addButton(nav)
            self.nav_buttons[key] = nav
            layout.addWidget(nav)

        layout.addStretch(1)

        status = QHBoxLayout()
        status.setSpacing(8)
        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("statusDot")
        self.status_dot.setStyleSheet(f"color: {PALETTE['subtle']};")
        self.status_text = QLabel("未运行")
        self.status_text.setObjectName("statusText")
        status.addWidget(self.status_dot)
        status.addWidget(self.status_text)
        status.addStretch(1)
        layout.addLayout(status)
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
        self.stack.setCurrentWidget(page)
        button = self.nav_buttons.get(key)
        if button is not None:
            button.setChecked(True)
        on_show = getattr(page, "on_show", None)
        if callable(on_show):
            on_show()

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

    def _on_server_state(self, running: bool) -> None:
        home = self.pages.get("home")
        if home is not None and hasattr(home, "set_running"):
            home.set_running(running)
        self.status_dot.setStyleSheet(
            f"color: {PALETTE['ok'] if running else PALETTE['subtle']};"
        )
        self.status_text.setText("运行中" if running else "未运行")
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
