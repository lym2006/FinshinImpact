# src/gui/dialogs/_settings/_field.py
"""字段渲染

- 按 schema 渲染表单控件与标签
- 持有控件表与标签表，恢复登记委托 ResetRegistry
"""

from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from utils.config import PENDING_MARK
from utils.config.models import (
    REQUIRED_KEYS,
    AppConfigData,
    AppSchema,
    ConfigValue,
    FieldSchema,
    TabData,
    is_blank,
)

from ..._theme import GLOBAL, SETTINGS_DIALOG
from ._list_widget import ConfigListWidget
from ._reset import Inputs, ResetRegistry

# Qt 布局四边
_MARGIN_EDGES = 4  # setContentsMargins 收上下左右四个值
_LABEL_WIDTH_MAX_EM = 8  # 标签列宽上限为 8 倍「M」字宽

_ERROR_QSS = f"color: {SETTINGS_DIALOG.error_color};"
_PENDING_QSS = f"color: {SETTINGS_DIALOG.pending_color};"

# 必填项空态渲染值：按模板默认类型呈现"未填写"的样子
_BLANK_BY_TYPE: dict[type, ConfigValue] = {
    str: "",
    float: "",
    bool: False,
    list: [],
}


class FieldBuilder:
    """字段渲染器

    - 持有控件表与标签表，供弹窗跨方法共享
    """

    def __init__(self, current: AppConfigData, font: QFont) -> None:
        self._current = current
        self._font = font
        self.inputs: Inputs = {}

        # {字段键: (标签控件, 原标题)}，复验结果原地刷新用
        self.labels: dict[str, tuple[QLabel, str]] = {}
        self._resets = ResetRegistry(self.inputs, self.value_of)

    def build(
        self,
        field: FieldSchema,
        namespace: str,
        errors: dict[str, str],
        label_width: int = 0,
    ) -> QWidget:
        """渲染表单控件

        - 必填键缺失或留空一律空态上屏
        - 非必填键缺失回退模板默认值
        """
        container = QWidget()
        form = QFormLayout(container)
        form.setSpacing(GLOBAL.radius)
        form.setContentsMargins(
            *[SETTINGS_DIALOG.margin] * (_MARGIN_EDGES - 1)
            + [SETTINGS_DIALOG.tab_spacing]
        )
        current_value, restore_target, required = self._resolve_value(field, namespace)
        label_widget = self._build_label(field, errors, label_width)

        # 列表型字段：恢复按钮挂进列表底栏
        if isinstance(field.default, list):
            list_widget = ConfigListWidget(
                items=current_value if isinstance(current_value, list) else [],
                description=field.desc,
            )
            self.inputs[field.key] = list_widget
            if not required:
                btn = list_widget.add_reset_button(
                    SETTINGS_DIALOG.reset_icon,
                    SETTINGS_DIALOG.reset_text,
                    lambda: self._resets.reset(field.key, restore_target),
                )
                self._resets.register(btn, field.key, field, restore_target)
            form.addRow(label_widget, list_widget)
            return container

        input_widget = self._build_input(field, current_value)
        self.inputs[field.key] = input_widget
        form.addRow(
            label_widget,
            self._build_right_side(field, input_widget, restore_target, required),
        )
        return container

    def label_width_of(self, fields: list[FieldSchema]) -> int:
        """计算标签统一列宽"""
        metrics = QFontMetrics(self._font)
        max_width = max((metrics.horizontalAdvance(f.label) for f in fields), default=0)
        limit = metrics.horizontalAdvance("M") * _LABEL_WIDTH_MAX_EM
        return min(max_width, limit)

    def value_of(self, field_key: str, field: FieldSchema) -> ConfigValue:
        """从控件提取字段当前值"""
        # float 解析失败返回原文，判定必不等于默认
        widget = self.inputs.get(field_key)
        if widget is None:
            return None
        match widget:
            case ConfigListWidget():
                return widget.get_values()
            case QCheckBox():
                return widget.isChecked()
            case QTextEdit():
                return widget.toPlainText().strip()
            case QLineEdit():
                text = widget.text().strip()
                if isinstance(field.default, float):
                    try:
                        return float(text)
                    except ValueError:
                        return text
                return text
        return None

    def collect(self, schema: AppSchema) -> AppConfigData:
        """从输入控件提取配置字典"""
        modified: AppConfigData = {}
        for tab in schema:
            tab_data: TabData = {}
            for field in tab.fields:
                tab_data[field.key] = self.value_of(field.key, field)
            modified[tab.namespace] = tab_data
        return modified

    def refresh_resets(self) -> None:
        """重估全部恢复按钮显隐"""
        self._resets.refresh()

    def _resolve_value(
        self, field: FieldSchema, namespace: str
    ) -> tuple[ConfigValue, ConfigValue, bool]:
        """取上屏值与恢复目标

        - 必填项空态上屏，不挂恢复按钮（占位假值不是可恢复的默认）
        - 非必填项恢复目标是模板默认值
        """
        # 禁模板占位假值冒充用户配置，用户不改即沿用默认值
        ns_config = self._current.get(namespace) or {}
        present = field.key in ns_config
        current_value: ConfigValue = ns_config[field.key] if present else field.default
        if f"{namespace}.{field.key}" not in REQUIRED_KEYS:
            restore_target: ConfigValue = (
                deepcopy(field.default)
                if isinstance(field.default, list)
                else field.default
            )
            return current_value, restore_target, False

        if not present or is_blank(current_value):
            current_value = _BLANK_BY_TYPE.get(type(field.default), "")
        return current_value, None, True

    def _build_label(
        self, field: FieldSchema, errors: dict[str, str], label_width: int
    ) -> QLabel:
        """构造字段标签

        - 出错字段标红
        """
        label_widget = QLabel(field.label)
        label_widget.setMinimumWidth(label_width)
        label_widget.setWordWrap(True)
        label_widget.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        if err := errors.get(field.key):
            if err.startswith(PENDING_MARK):
                # 前置项失败导致的"暂未检测"：黄字 ❔，不算本项错误
                label_widget.setText(f"❔ {field.label}")
                label_widget.setStyleSheet(_PENDING_QSS)
            else:
                label_widget.setStyleSheet(_ERROR_QSS)
            label_widget.setToolTip(err)
        self.labels[field.key] = (label_widget, field.label)
        return label_widget

    def _build_input(
        self, field: FieldSchema, current_value: ConfigValue
    ) -> QCheckBox | QTextEdit | QLineEdit:
        """按值形态选控件

        - bool 项走勾选框，勾选框自身不挂文字，标签与说明走通用右侧结构
        - 含换行的字符串走多行编辑
        """
        if isinstance(field.default, bool):
            bool_box = QCheckBox()
            bool_box.setChecked(bool(current_value))
            return bool_box
        if isinstance(current_value, str) and "\n" in current_value:
            editor = QTextEdit()
            editor.setPlainText(current_value)
            return editor
        display = str(current_value) if current_value is not None else ""
        return QLineEdit(display)

    def _build_right_side(
        self,
        field: FieldSchema,
        input_widget: QWidget,
        restore_target: ConfigValue,
        required: bool,
    ) -> QWidget:
        """构造右侧区域

        - 输入框（可带恢复按钮） + 说明文字
        """
        right_wrapper = QWidget()
        v_layout = QVBoxLayout(right_wrapper)
        v_layout.setContentsMargins(*[SETTINGS_DIALOG.margin] * _MARGIN_EDGES)
        v_layout.setSpacing(SETTINGS_DIALOG.desc_spacing)
        if required:
            v_layout.addWidget(input_widget)
        else:
            row, btn = self._resets.wrap(input_widget, field.key, restore_target)
            self._resets.register(btn, field.key, field, restore_target)
            v_layout.addWidget(row)
        if field.desc:
            desc_label = QLabel(field.desc)
            desc_label.setWordWrap(True)
            v_layout.addWidget(desc_label)
        return right_wrapper
