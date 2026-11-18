"""字段渲染

- 按 schema 渲染表单控件与标签
- 持有控件表与标签表，恢复登记另交一只登记表件
"""

from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from finshin_sdk.domain import ConfigPath
from skin.qss import build_error_label_qss
from skin.theme import GLOBAL, SETTINGS_DIALOG
from utils.config import AppConfigData, AppSchema, FieldErrors
from utils.config.models import ConfigValue, FieldSchema, TabData, TabSchema, is_blank

from ..._primitives import make_combo, set_margins
from ._list_widget import ConfigListRow
from ._reset import Inputs, ResetRegistry

_LABEL_WIDTH_MAX_EM = 8  # 标签列宽上限为 8 倍「M」字宽

# 必填项空态渲染值：按默认值类型呈现"未填写"的样子
_BLANK_BY_TYPE: dict[type, ConfigValue] = {
    str: "",
    list: [],
}


def refresh_label(label: QLabel, title: str, err: str | None) -> None:
    """按校验结果刷新一个字段标签

    - 本项有错即标红，无错即清样式
    """
    if err:
        label.setText(title)
        label.setStyleSheet(build_error_label_qss())
    else:
        label.setText(title)
        label.setStyleSheet("")
    label.setToolTip(err or "")


class FieldBuilder:
    """字段渲染器

    - 持有控件表与标签表，供弹窗跨方法共享
    """

    def __init__(self, current: AppConfigData, font: QFont) -> None:
        self._current = current
        self._font = font
        self.inputs: Inputs = {}

        # {配置项身份: (标签控件, 原标题)}，复验结果原地刷新用
        self.labels: dict[ConfigPath, tuple[QLabel, str]] = {}
        self._resets = ResetRegistry(self.inputs, self.value_of)

    def build(
        self,
        tab: TabSchema,
        field: FieldSchema,
        errors: FieldErrors,
        label_width: int = 0,
    ) -> QWidget:
        """渲染表单控件

        - 必填键缺失或留空一律空态上屏
        - 非必填键缺失回退默认值
        """
        container = QWidget()
        form = QFormLayout(container)
        form.setSpacing(GLOBAL.radius)
        set_margins(form, SETTINGS_DIALOG.margin, bottom=SETTINGS_DIALOG.tab_spacing)
        current_value, restore_target, required = self._resolve_value(
            field, tab.section
        )
        item = tab.path_of(field)
        label_widget = self._build_label(item, field, errors, label_width)

        input_widget = self._build_input(field, current_value)
        self.inputs[item] = input_widget
        form.addRow(
            label_widget,
            self._build_right_side(item, field, input_widget, restore_target, required),
        )
        return container

    def label_width_of(self, fields: list[FieldSchema]) -> int:
        """计算标签统一列宽"""
        metrics = QFontMetrics(self._font)
        max_width = max((metrics.horizontalAdvance(f.label) for f in fields), default=0)
        limit = metrics.horizontalAdvance("M") * _LABEL_WIDTH_MAX_EM
        return min(max_width, limit)

    def value_of(self, item: ConfigPath, field: FieldSchema) -> ConfigValue:
        """从控件提取字段当前值"""
        # float 解析失败返回原文，判定必不等于默认
        widget = self.inputs.get(item)
        if widget is None:
            return None
        match widget:
            case ConfigListRow():
                return widget.get_values()
            case QComboBox():
                return widget.currentData()
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
                tab_data[field.key] = self.value_of(tab.path_of(field), field)
            modified[tab.section] = tab_data
        return modified

    def refresh_resets(self) -> None:
        """重估全部恢复按钮显隐"""
        self._resets.refresh()

    def _resolve_value(
        self, field: FieldSchema, section: str
    ) -> tuple[ConfigValue, ConfigValue, bool]:
        """取上屏值与恢复目标

        - 必填项空态上屏且不挂恢复按钮
        - 非必填项恢复目标是默认值
        """
        # 禁默认值假值冒充用户配置，用户不改即用默认值
        section_data = self._current.get(section) or {}
        present = field.key in section_data
        current_value: ConfigValue = (
            section_data[field.key] if present else field.default
        )
        if not field.required:
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
        self,
        item: ConfigPath,
        field: FieldSchema,
        errors: FieldErrors,
        label_width: int,
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
        refresh_label(label_widget, field.label, errors.get(item))
        self.labels[item] = (label_widget, field.label)
        return label_widget

    def _build_input(
        self, field: FieldSchema, current_value: ConfigValue
    ) -> QComboBox | QTextEdit | QLineEdit | ConfigListRow:
        """按值形态选控件

        - 枚举项渲染下拉，显示文案挂 userData 取键值
        - 列表项收成入口行，内容在弹窗里改
        - 含换行的字符串走多行编辑
        """
        if isinstance(field.default, list):
            items = current_value if isinstance(current_value, list) else []
            return ConfigListRow(field.label, items)
        if field.options:
            combo = make_combo(field.options)
            index = combo.findData(current_value)
            if index < 0:
                # 手改的非法枚举值原样入列，标红引导改回而非吞值
                combo.addItem(str(current_value), current_value)
                index = combo.count() - 1
            combo.setCurrentIndex(index)
            return combo
        if isinstance(current_value, str) and "\n" in current_value:
            editor = QTextEdit()
            editor.setPlainText(current_value)
            return editor
        display = str(current_value) if current_value is not None else ""
        return QLineEdit(display)

    def _build_right_side(
        self,
        item: ConfigPath,
        field: FieldSchema,
        input_widget: QWidget,
        restore_target: ConfigValue,
        required: bool,
    ) -> QWidget:
        """构造右侧区域

        - 输入框与可选恢复按钮，外加说明文字
        - 枚举项不挂恢复钮：选中即意图，无"偏离默认"可恢复
        """
        right_wrapper = QWidget()
        v_layout = QVBoxLayout(right_wrapper)
        set_margins(v_layout, SETTINGS_DIALOG.margin)
        v_layout.setSpacing(SETTINGS_DIALOG.desc_spacing)
        if required or field.options:
            v_layout.addWidget(input_widget)
        else:
            row, btn = self._resets.wrap(input_widget, item, restore_target)
            self._resets.register(btn, item, field, restore_target)
            v_layout.addWidget(row)
        if field.desc:
            desc_label = QLabel(field.desc)
            desc_label.setWordWrap(True)
            v_layout.addWidget(desc_label)
        return right_wrapper
