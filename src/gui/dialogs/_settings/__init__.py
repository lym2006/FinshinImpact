# src/gui/dialogs/_settings/__init__.py
"""配置向导

- 实现多标签页表单与错误标红
- 提供复验结果原地刷新与防重入
"""

from enum import Enum, auto

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QFont, QKeyEvent, QShowEvent
from PySide6.QtWidgets import QWidget

from utils.config import PENDING_MARK
from utils.config.models import AppConfigData, AppSchema

from ..._qss import build_settings_dialog_qss
from ..._theme import SETTINGS_DIALOG
from ...mediator import gui_bridge
from .._base import BaseDialog
from ._change import ChangeConfirmDialog
from ._chrome import ChromeBuilder
from ._field import FieldBuilder

__all__ = [
    "ChangeConfirmDialog",
    "ConfigMode",
    "SettingsDialog",
]

_ERROR_QSS = f"color: {SETTINGS_DIALOG.error_color};"
_PENDING_QSS = f"color: {SETTINGS_DIALOG.pending_color};"
_ERROR_FONT = QFont(SETTINGS_DIALOG.error_font_family, SETTINGS_DIALOG.error_font_size)


class ConfigMode(Enum):
    """配置弹窗的工作模式"""

    EDIT = auto()  # 正常编辑（用户主动点击）
    SETUP = auto()  # 缺失引导（验证失败强制弹出）


class SettingsDialog(BaseDialog):
    """配置面板弹窗

    - 表单渲染交 FieldBuilder，骨架装配交 ChromeBuilder
    """

    # SETUP 模式请求保存：由控制器校验并决定是否关窗，窗口自身不 accept
    save_requested = Signal()

    def __init__(
        self,
        schema: AppSchema,
        current_config: AppConfigData,
        mode: ConfigMode = ConfigMode.EDIT,
        parent: QWidget | None = None,
        field_errors: dict[str, str] | None = None,
    ) -> None:
        super().__init__(parent=parent, title=SETTINGS_DIALOG.title)

        # SETUP 模式字段级错误：{字段键: 悬浮文案}
        self._field_errors: dict[str, str] = dict(field_errors or {})

        # 出错字段所在 namespace，用于标红对应标签页
        self._error_namespaces = self._resolve_error_namespaces(schema)
        self.setStyleSheet(build_settings_dialog_qss())
        self._schema = schema
        self._mode = mode

        self._fields = FieldBuilder(current_config, self.font())
        self._chrome = ChromeBuilder(
            host=self,
            fields=self._fields,
            errors=self._field_errors,
            error_qss=_ERROR_QSS,
            error_font=_ERROR_FONT,
            on_exit=self._on_exit_clicked,
            on_cancel=self.reject,
            on_save=self.save_requested.emit,
        )

        # 非模态 + 灰×，防误点错觉，EDIT 退出走取消/Esc，SETUP 走 closeEvent 拦截
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)

        self.setMinimumSize(SETTINGS_DIALOG.min_width, SETTINGS_DIALOG.min_height)
        self._chrome.build(schema, self._is_setup(), self._error_namespaces)

    def _is_setup(self) -> bool:
        """当前是否 SETUP 模式"""
        return self._mode == ConfigMode.SETUP

    # 关闭与退出
    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """SETUP 模式拦截自身关闭"""
        if self._is_setup():
            event.ignore()
        else:
            super().closeEvent(event)

    def showEvent(self, event: QShowEvent) -> None:  # noqa: N802
        """每次显示重估恢复按钮显隐

        - 以控件当前值判定
        """
        # 覆盖首次打开与已开后置前两条路径
        super().showEvent(event)
        self._fields.refresh_resets()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """SETUP 屏蔽 Esc

        - 防绕过不可关闭约束
        """
        if self._is_setup() and event.key() == Qt.Key.Key_Escape:
            event.accept()
            return
        super().keyPressEvent(event)

    def _on_exit_clicked(self) -> None:
        """退出程序

        - 保留本窗请求退出
        """
        # 确认框取消时本窗与已填内容原样保留
        gui_bridge.request_exit.emit(self)

    # 错误标注
    def _resolve_error_namespaces(self, schema: AppSchema) -> set[str]:
        """定位出错字段所在页"""
        bad: set[str] = set()
        for tab in schema:
            if any(f.key in self._field_errors for f in tab.fields):
                bad.add(tab.namespace)
        return bad

    def apply_errors(self, field_errors: dict[str, str] | None) -> None:
        """原地刷新校验结果

        - 字段标红/清除
        - 标签页 ⚠ 增撤
        """
        self._field_errors = dict(field_errors or {})
        bad = self._resolve_error_namespaces(self._schema)
        for key, (label, title) in self._fields.labels.items():
            err = self._field_errors.get(key)
            if err and err.startswith(PENDING_MARK):
                label.setText(f"❔ {title}")
                label.setStyleSheet(_PENDING_QSS)
            elif err:
                label.setText(title)
                label.setStyleSheet(_ERROR_QSS)
            else:
                label.setText(title)
                label.setStyleSheet("")
            label.setToolTip(err or "")
        for ns, (index, title) in self._chrome.tab_titles.items():
            mark = "⚠ " if ns in bad else ""
            if self._chrome.tabs is None:
                continue
            self._chrome.tabs.setTabText(index, f"{mark}{title}")
        self._fields.refresh_resets()

    def set_busy(self, busy: bool) -> None:
        """校验进行中的防重入

        - 锁表单与保存按钮
        """
        if self._chrome.save_btn is None:
            return
        self._chrome.save_btn.setEnabled(not busy)
        self._chrome.save_btn.setText(
            SETTINGS_DIALOG.validating_text if busy else self._chrome.save_text
        )
        if self._chrome.tabs is not None:
            self._chrome.tabs.setEnabled(not busy)

    def switch_to_setup(self, field_errors: dict[str, str] | None) -> None:
        """EDIT 原地转 SETUP

        - 保内容、换按钮、挂提示
        """
        # 只拆提示行与按钮条两个可再生部件，模态与×两模式同款出生定死，无需动
        self._mode = ConfigMode.SETUP
        self._field_errors = dict(field_errors or {})
        self._error_namespaces = self._resolve_error_namespaces(self._schema)
        self._chrome.rebuild(self._is_setup())
        self.apply_errors(self._field_errors)

    def get_modified_config(self) -> AppConfigData:
        """从输入控件提取配置字典"""
        return self._fields.collect(self._schema)
