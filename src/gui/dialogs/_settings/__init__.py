# src/gui/dialogs/_settings/__init__.py
"""配置向导（内部实现）

- 实现多标签页表单与错误标红
- 提供复验结果原地刷新与防重入
"""

from enum import Enum, auto

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QFont, QFontMetrics, QKeyEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from utils.config import PENDING_MARK
from utils.config.models import (
    AppConfigData,
    AppSchema,
    ConfigValue,
    FieldSchema,
    TabData,
    TabSchema,
)

from ..._qss import build_settings_dialog_qss
from ..._theme import GLOBAL, SETTINGS_DIALOG
from ...mediator import gui_bridge
from .._base import BaseDialog
from ._change import ChangeConfirmDialog
from ._list_widget import ConfigListWidget

__all__ = [
    "ChangeConfirmDialog",
    "ConfigMode",
    "SettingsDialog",
]

_ERROR_QSS = f"color: {SETTINGS_DIALOG.error_color};"
_PENDING_QSS = f"color: {SETTINGS_DIALOG.pending_color};"
_ERROR_FONT = QFont(SETTINGS_DIALOG.error_font_family, SETTINGS_DIALOG.error_font_size)


def _clear_layout(layout: QHBoxLayout) -> None:
    """腾空按钮条：逐项摘控件交还 GC，容器自身由调用方 removeItem"""
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().deleteLater()


class ConfigMode(Enum):
    """配置弹窗的工作模式"""

    EDIT = auto()  # 正常编辑（用户主动点击）
    SETUP = auto()  # 缺失引导（验证失败强制弹出）


class SettingsDialog(BaseDialog):
    """配置面板弹窗"""

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
        self._current = current_config
        self._mode = mode

        # 输入控件表：{"field_key": widget}
        self._inputs: dict[
            str,
            ConfigListWidget | QLineEdit | QTextEdit | QCheckBox,
        ] = {}

        # 标签/页签/按钮引用：复验结果原地刷新用（免关窗重开的闪烁）
        self._labels: dict[str, tuple[QLabel, str]] = {}
        self._tab_titles: dict[str, tuple[int, str]] = {}
        self._tabs: QTabWidget | None = None
        self._save_btn: QPushButton | None = None
        self._save_text: str = ""

        # 根布局/按钮条/提示行引用：原地切模式只拆可再生部件，表单永不重建
        self._root_layout: QVBoxLayout | None = None
        self._bottom_layout: QHBoxLayout | None = None
        self._tip_labels: list[QLabel] = []

        # 非模态 + 灰×：两模式同款，×开关只在 flags 上，出生定死终身不碰
        # 摘×防误点错觉；EDIT 退出走取消/Esc，SETUP 走 closeEvent 拦截
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)

        self.setMinimumSize(SETTINGS_DIALOG.min_width, SETTINGS_DIALOG.min_height)
        self._build_ui()

    # ==================== 关闭与退出 ====================

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """SETUP 模式拦截自身关闭"""
        if self._mode == ConfigMode.SETUP:
            event.ignore()
        else:
            super().closeEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """SETUP 屏蔽 Esc

        防绕过不可关闭约束。
        """
        if self._mode == ConfigMode.SETUP and event.key() == Qt.Key.Key_Escape:
            event.accept()
            return
        super().keyPressEvent(event)

    def _on_exit_clicked(self) -> None:
        """退出程序

        保留本窗请求退出
        确认框取消时本窗与已填内容原样保留。
        """
        gui_bridge.request_exit.emit(self)

    # ==================== 错误标注 ====================

    def _resolve_error_namespaces(self, schema: AppSchema) -> set[str]:
        """定位出错字段所在页"""
        bad: set[str] = set()
        for tab in schema:
            if any(f.key in self._field_errors for f in tab.fields):
                bad.add(tab.namespace)
        return bad

    def apply_errors(self, field_errors: dict[str, str] | None) -> None:
        """原地刷新校验结果

        字段标红/清除、标签页 ⚠ 增撤
        """
        self._field_errors = dict(field_errors or {})
        bad = self._resolve_error_namespaces(self._schema)
        for key, (label, title) in self._labels.items():
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
        for ns, (index, title) in self._tab_titles.items():
            mark = "⚠ " if ns in bad else ""
            if self._tabs is None:
                continue
            self._tabs.setTabText(index, f"{mark}{title}")

    def set_busy(self, busy: bool) -> None:
        """校验进行中的防重入

        锁表单与保存按钮：校验结果只对应按下瞬间的配置，改不动才不会被吞。
        """
        if self._save_btn is None:
            return
        self._save_btn.setEnabled(not busy)
        self._save_btn.setText(
            SETTINGS_DIALOG.validating_text if busy else self._save_text
        )
        if self._tabs is not None:
            self._tabs.setEnabled(not busy)

    def switch_to_setup(self, field_errors: dict[str, str] | None) -> None:
        """EDIT 原地转 SETUP：保内容、换按钮、挂提示

        只拆提示行与按钮条两个可再生部件；模态与×两模式同款出生定死，无需动。
        """
        self._mode = ConfigMode.SETUP
        self._field_errors = dict(field_errors or {})
        self._error_namespaces = self._resolve_error_namespaces(self._schema)
        self._rebuild_chrome()
        self.apply_errors(self._field_errors)

    def _rebuild_chrome(self) -> None:
        """拆建提示行与底部按钮条"""
        if self._root_layout is None:
            return
        for tip in self._tip_labels:
            self._root_layout.removeWidget(tip)
            tip.deleteLater()
        self._tip_labels.clear()
        if self._bottom_layout is not None:
            self._root_layout.removeItem(self._bottom_layout)
            _clear_layout(self._bottom_layout)
        if self._mode == ConfigMode.SETUP:
            tip_label = QLabel(SETTINGS_DIALOG.setup_tip)
            tip_label.setStyleSheet(_ERROR_QSS)
            tip_label.setFont(_ERROR_FONT)
            hint_label = QLabel(SETTINGS_DIALOG.setup_hint)
            hint_label.setStyleSheet(_ERROR_QSS)
            self._root_layout.insertWidget(0, tip_label)
            self._root_layout.insertWidget(1, hint_label)
            self._tip_labels = [tip_label, hint_label]
        self._bottom_layout = self._build_bottom_buttons()
        self._root_layout.addLayout(self._bottom_layout)

    # ==================== 渲染 ====================

    def _create_field(
        self, field: FieldSchema, namespace: str, label_width: int = 0
    ) -> QWidget:
        """渲染表单控件"""
        container = QWidget()
        form = QFormLayout(container)
        form.setSpacing(GLOBAL.radius)
        form.setContentsMargins(
            *[SETTINGS_DIALOG.margin] * 3 + [SETTINGS_DIALOG.tab_spacing]
        )
        ns_config = self._current.get(namespace)
        current_value = (
            ns_config[field.key]
            if ns_config and field.key in ns_config
            else field.default
        )

        # 标签：出错字段标红
        label_widget = QLabel(field.label)
        label_widget.setMinimumWidth(label_width)
        label_widget.setWordWrap(True)
        label_widget.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        if err := self._field_errors.get(field.key):
            if err.startswith(PENDING_MARK):
                # 前置项失败导致的"暂未检测"：黄字 ❔，不算本项错误
                label_widget.setText(f"❔ {field.label}")
                label_widget.setStyleSheet(_PENDING_QSS)
            else:
                label_widget.setStyleSheet(_ERROR_QSS)
            label_widget.setToolTip(err)
        self._labels[field.key] = (label_widget, field.label)

        # 列表型字段
        if isinstance(field.default, list):
            list_widget = ConfigListWidget(
                items=current_value if isinstance(current_value, list) else [],
                description=field.desc,
            )
            self._inputs[field.key] = list_widget
            form.addRow(label_widget, list_widget)
            return container

        # bool 配置项 → 勾选行（通用机制，避免 True/False 一行丑字）
        input_widget: QWidget
        if isinstance(field.default, bool):
            bool_box = QCheckBox(field.label)
            bool_box.setChecked(bool(current_value))
            self._inputs[field.key] = bool_box
            form.addRow(field.label, bool_box)
            return container
        if isinstance(current_value, str) and "\n" in current_value:
            input_widget = QTextEdit()
            input_widget.setPlainText(current_value)
        else:
            display = str(current_value) if current_value is not None else ""
            input_widget = QLineEdit(display)

        self._inputs[field.key] = input_widget

        # 右侧区域：输入框 + 说明文字
        right_wrapper = QWidget()
        v_layout = QVBoxLayout(right_wrapper)
        v_layout.setContentsMargins(*[SETTINGS_DIALOG.margin] * 4)
        v_layout.setSpacing(SETTINGS_DIALOG.desc_spacing)
        v_layout.addWidget(input_widget)
        if field.desc:
            v_layout.addWidget(self._build_desc(field.desc))

        form.addRow(label_widget, right_wrapper)
        return container

    def _calc_label_width(self, fields: list[FieldSchema]) -> int:
        """计算标签统一列宽"""
        metrics = QFontMetrics(self.font())
        max_width = max((metrics.horizontalAdvance(f.label) for f in fields), default=0)
        limit = metrics.horizontalAdvance("M") * 8
        return min(max_width, limit)

    def _build_desc(self, text: str) -> QLabel:
        """说明文字标签"""
        label = QLabel(text)
        label.setWordWrap(True)
        return label

    # ==================== 数据提取 ====================

    def get_modified_config(self) -> AppConfigData:
        """从输入控件提取配置字典"""
        modified: AppConfigData = {}

        for tab in self._schema:
            tab_data: TabData = {}

            for field in tab.fields:
                widget = self._inputs.get(field.key)
                value: ConfigValue = None

                if widget:
                    if isinstance(widget, ConfigListWidget):
                        value = widget.get_values()
                    elif isinstance(widget, QTextEdit):
                        value = widget.toPlainText().strip()
                    elif isinstance(widget, QCheckBox):
                        value = widget.isChecked()
                    elif isinstance(widget, QLineEdit):
                        text = widget.text().strip()
                        if isinstance(field.default, float):
                            try:
                                value = float(text)
                            except ValueError:
                                value = text  # 保持原样，交给类型校验器报错
                        else:
                            value = text

                tab_data[field.key] = value
            modified[tab.namespace] = tab_data
        return modified

    # ==================== 骨架 ====================

    def _build_ui(self) -> None:
        """构建界面"""
        root_layout = QVBoxLayout(self)
        self._root_layout = root_layout
        root_layout.setContentsMargins(
            *([SETTINGS_DIALOG.input_padding_h, SETTINGS_DIALOG.input_padding_v] * 2)
        )
        root_layout.setSpacing(SETTINGS_DIALOG.tab_spacing)

        # SETUP 提示：出错标签页带 ⚠，出错字段标题标红
        if self._mode == ConfigMode.SETUP:
            tip_label = QLabel(SETTINGS_DIALOG.setup_tip)
            tip_label.setStyleSheet(_ERROR_QSS)
            tip_label.setFont(_ERROR_FONT)
            hint_label = QLabel(SETTINGS_DIALOG.setup_hint)
            hint_label.setStyleSheet(_ERROR_QSS)
            root_layout.addWidget(tip_label)
            root_layout.addWidget(hint_label)
            self._tip_labels = [tip_label, hint_label]

        tabs = QTabWidget()
        for index, tab_schema in enumerate(self._schema):
            tab_widget = self._create_tab(tab_schema)
            mark = "⚠ " if tab_schema.namespace in self._error_namespaces else ""
            tabs.addTab(tab_widget, f"{mark}{tab_schema.title}")
            self._tab_titles[tab_schema.namespace] = (index, tab_schema.title)
        self._tabs = tabs
        root_layout.addWidget(tabs)
        self._bottom_layout = self._build_bottom_buttons()
        root_layout.addLayout(self._bottom_layout)

    def _create_tab(self, tab_schema: TabSchema) -> QWidget:
        """创建一个 Tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setAutoFillBackground(False)
        container = QWidget()
        container.setStyleSheet(f"background-color: {SETTINGS_DIALOG.tab_bg};")
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(SETTINGS_DIALOG.tab_spacing)
        label_width = self._calc_label_width(tab_schema.fields)
        for field in tab_schema.fields:
            main_layout.addWidget(
                self._create_field(field, tab_schema.namespace, label_width)
            )
        main_layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _build_bottom_buttons(self) -> QHBoxLayout:
        """按模式构建底部按钮"""
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(GLOBAL.radius)
        btn_layout.addStretch()

        match self._mode:
            case ConfigMode.EDIT:
                btn_cancel = QPushButton(SETTINGS_DIALOG.cancel_text)
                btn_cancel.clicked.connect(self.reject)
                btn_save = QPushButton(SETTINGS_DIALOG.save_text)
                btn_save.setObjectName("btn_primary")
                btn_save.clicked.connect(self.save_requested.emit)
                self._save_btn, self._save_text = btn_save, SETTINGS_DIALOG.save_text
                btn_layout.addWidget(btn_cancel)
                btn_layout.addWidget(btn_save)
            case ConfigMode.SETUP:
                btn_exit = QPushButton(SETTINGS_DIALOG.exit_text)
                btn_exit.clicked.connect(self._on_exit_clicked)
                btn_finish = QPushButton(SETTINGS_DIALOG.finish_text)
                btn_finish.setObjectName("btn_primary")
                btn_finish.setMinimumWidth(SETTINGS_DIALOG.finish_btn_min_width)

                # 发信号而非 accept：校验通过才关窗，失败则原窗保留已填内容
                btn_finish.clicked.connect(self.save_requested.emit)
                self._save_btn, self._save_text = (
                    btn_finish,
                    SETTINGS_DIALOG.finish_text,
                )
                btn_layout.addWidget(btn_exit)
                btn_layout.addWidget(btn_finish)

        return btn_layout
