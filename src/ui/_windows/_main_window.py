"""主窗口

- BotGUI 渲染与指令执行层
"""

import logging
from collections.abc import Callable

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from skin.theme import (
    BodyTheme,
    ButtonSize,
    ButtonStyle,
    FontTheme,
    ObjectName,
    WindowTheme,
)
from utils import get_logger

from .._dialogs import (
    NoticeDialog,
    PersonaResolveDialog,
    PersonaSyncDialog,
)
from .._lifecycle import Ticker
from .._primitives import BaseDialog, make_button
from ._dashboard import DashboardWidget, TextHandler

# 通知重试
_NOTICE_RETRY_DELAY_MS = 800  # 模态占用时 0.8 秒后重弹

# 走危险色的工具栏动作
_DANGER_ACTIONS = frozenset({"clear", "shutdown"})


def _result_owner(fallback: QWidget) -> QWidget | None:
    """结果窗该挂的那只窗

    - 有模态窗开着就挂它，结果浮在它上面，也只拦它
    - 交回 None 表示此刻该等
    """
    modal = QApplication.activeModalWidget()
    # 判据见 BaseDialog.RESULT_WINDOW
    if isinstance(modal, BaseDialog) and modal.RESULT_WINDOW:
        return None
    return modal or fallback


class BotGUI(QMainWindow):
    """Bot 可视化窗口

    - 纯渲染与指令执行
    """

    def __init__(
        self,
        qss: str,
        buttons: list[tuple[str, str]],
        configs: tuple[FontTheme, WindowTheme, BodyTheme],
        formatter: logging.Formatter,
    ) -> None:

        super().__init__()
        self._qss = qss
        self._buttons = buttons

        self._fonts, self._windows, self._body = configs

        self._hidden_actions = {"shutdown"}  # 不渲染只回调的按钮
        self._logger = get_logger("GUI")

        self.setWindowTitle(self._windows.title)
        self.resize(self._windows.width, self._windows.height)
        self.setMinimumSize(self._windows.min_width, self._windows.min_height)

        # 按钮事件映射表（按钮 ID -> 已包装的回调函数）
        self.action_map: dict[str, Callable] = {}

        # 致命错误确认后的直退句柄（由 Main 注入）
        self._shutdown_handler: Callable[[], None] | None = None

        # 仪表盘与文本处理器（纯 UI 组件，内部实例化）
        self._dashboard = DashboardWidget(self._fonts)
        self._text_handler: logging.Handler = TextHandler(self._dashboard, formatter)

        self._build_ui()

    def _build_ui(self) -> None:
        """组装窗口的整体布局结构"""
        central = QWidget()  # 中央容器
        central.setObjectName(ObjectName.CENTRAL)
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(self._body.padding)

        self._build_toolbar(main_layout)

        main_layout.addWidget(self._dashboard)

        self.setStyleSheet(self._qss)

    def _build_toolbar(self, parent_layout: QVBoxLayout) -> None:
        """渲染顶部工具栏

        - 清空单独贴右，其余靠左
        """
        toolbar = QWidget()
        toolbar.setObjectName(ObjectName.TOOLBAR)
        row = QHBoxLayout(toolbar)
        row.setSpacing(self._body.padding)

        visible = [
            (text, key)
            for text, key in self._buttons
            if key not in self._hidden_actions
        ]

        def add(text: str, key: str) -> None:
            btn_id = f"btn_{key}"
            style = (
                ButtonStyle.DANGER if key in _DANGER_ACTIONS else ButtonStyle.NEUTRAL
            )
            row.addWidget(
                make_button(
                    text,
                    style,
                    size=ButtonSize.COMPACT,
                    on_click=lambda checked=False, bid=btn_id: self._handle_button(bid),
                )
            )

        for text, key in visible:
            if key not in _DANGER_ACTIONS:
                add(text, key)
        row.addStretch()
        for text, key in visible:
            if key in _DANGER_ACTIONS:
                add(text, key)

        parent_layout.addWidget(toolbar)

    def _handle_button(self, btn_id: str) -> None:
        """响应按钮点击事件"""
        action = self.action_map.get(btn_id)

        if not action:
            self._logger.debug(f"按钮 {btn_id} 没接动作")
            return

        self._logger.debug(f"按钮 {btn_id} 按下")
        action()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """拦截窗口关闭"""
        event.ignore()
        self._handle_button("btn_shutdown")

    def set_action_map(self, action_map: dict[str, Callable]) -> None:
        """注入按钮 ID 与回调函数的映射"""
        self.action_map = action_map

    def set_logger_handler(self) -> None:
        """挂载仪表盘日志处理器"""
        root_logger = get_logger()

        if (handler := self._text_handler) not in root_logger.handlers:
            handler.setLevel(logging.INFO)
            root_logger.addHandler(handler)

    def clear_dashboard(self) -> None:
        """清空仪表盘内容"""
        self._dashboard.clear()

    def set_shutdown_handler(self, handler: Callable[[], None]) -> None:
        """注入致命错误后的直退句柄"""
        self._shutdown_handler = handler

    def show_notice(
        self, message: str, critical: bool = False, bold: bool = False
    ) -> None:
        """弹出统一通知

        - critical 为致命通知，确认后直接退出
        - bold 加粗正文，给当场生效、容易被看漏的提示用
        - 多行长文整段交弹窗
        """
        owner = _result_owner(self)
        if owner is None:
            Ticker.after(
                _NOTICE_RETRY_DELAY_MS,
                lambda: self.show_notice(message, critical, bold),
            )
            return

        if critical:
            self._logger.error(f"致命错误: {message}")

        box = NoticeDialog(message, critical=critical, parent=owner, bold=bold)
        box.raise_()
        box.activateWindow()
        box.exec()

        if critical and self._shutdown_handler is not None:
            self._shutdown_handler()

    def show_persona_update(self) -> None:
        """弹出内置模板更新提示"""
        owner = _result_owner(self)
        if owner is None:
            Ticker.after(_NOTICE_RETRY_DELAY_MS, self.show_persona_update)
            return

        PersonaSyncDialog.notify_update(parent=owner)

    def show_persona_resolve(
        self, old: str, new: str, old_label: str, new_label: str
    ) -> None:
        """弹出人设拍板窗"""
        owner = _result_owner(self)
        if owner is None:
            Ticker.after(
                _NOTICE_RETRY_DELAY_MS,
                lambda: self.show_persona_resolve(old, new, old_label, new_label),
            )
            return

        PersonaResolveDialog(old, new, old_label, new_label, parent=owner).exec()
