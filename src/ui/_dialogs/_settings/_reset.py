"""恢复默认登记

- 按控件当前值重估恢复按钮显隐
- 回填目标值并刷新显隐
"""

from collections.abc import Callable
from typing import TypeAlias

from PySide6.QtCore import SignalInstance
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QWidget,
)

from finshin_sdk.domain import ConfigPath
from skin.theme import SETTINGS_DIALOG, ButtonStyle
from utils.config.models import ConfigValue, FieldSchema

from ..._primitives import make_button, set_margins
from ._list_widget import ConfigListRow

_InputWidget: TypeAlias = ConfigListRow | QLineEdit | QTextEdit | QComboBox
Inputs: TypeAlias = dict[ConfigPath, _InputWidget]


def _value_signal(widget: _InputWidget) -> SignalInstance | None:
    """取控件的值变化信号源

    - 入口行只在弹窗确认时广播一次
    - 枚举下拉不登记恢复钮，无信号可挂
    """
    match widget:
        case ConfigListRow():
            return widget.items_changed
        case QTextEdit():
            return widget.textChanged
        case QLineEdit():
            return widget.textChanged
    return None


class ResetRegistry:
    """恢复默认登记

    - 按控件当前值重估按钮显隐并回填
    """

    def __init__(
        self,
        inputs: Inputs,
        value_of: Callable[[ConfigPath, FieldSchema], ConfigValue],
    ) -> None:
        self._inputs = inputs
        self._value_of = value_of

        # {配置项身份: (按钮, 字段, 恢复目标)}
        self._rows: dict[ConfigPath, tuple[QPushButton, FieldSchema, ConfigValue]] = {}

    def wrap(
        self, widget: QWidget, item: ConfigPath, restore_target: ConfigValue
    ) -> tuple[QWidget, QPushButton]:
        """输入控件右侧挂恢复按钮"""
        # 图标态，悬停出提示
        row = QWidget()
        h_layout = QHBoxLayout(row)
        set_margins(h_layout, SETTINGS_DIALOG.margin)
        h_layout.setSpacing(SETTINGS_DIALOG.desc_spacing)
        h_layout.addWidget(widget, stretch=1)
        btn = make_button(SETTINGS_DIALOG.reset_icon, ButtonStyle.RESET)
        btn.setToolTip(SETTINGS_DIALOG.reset_text)

        # 恢复只回填控件：落盘仍走正常保存链路，确认环节由 diff 窗把
        btn.clicked.connect(lambda: self.reset(item, restore_target))
        h_layout.addWidget(btn)
        return row, btn

    def register(
        self,
        btn: QPushButton,
        item: ConfigPath,
        field: FieldSchema,
        restore_target: ConfigValue,
    ) -> None:
        """登记恢复按钮

        - 初始隐藏
        - 控件值一变即重估全部按钮
        """
        # 显隐统一交给刷新时机判定
        btn.setVisible(False)
        self._rows[item] = (btn, field, restore_target)
        widget = self._inputs.get(item)
        if widget is not None and (sig := _value_signal(widget)) is not None:
            sig.connect(self.refresh)

    def refresh(self) -> None:
        """重估全部恢复按钮显隐

        - 逐项按当前值比对恢复目标
        - 面板打开与校验回传时各刷一次
        """
        # 判定对象是控件里的当前值而非磁盘快照，手改待保存的偏离同样亮钮
        for item, (btn, field, restore_target) in self._rows.items():
            btn.setVisible(self._value_of(item, field) != restore_target)

    def reset(self, item: ConfigPath, restore_target: ConfigValue) -> None:
        """按控件类型回填恢复目标值

        - 回填后重估按钮显隐
        """
        widget = self._inputs.get(item)
        if widget is None:
            return
        text = "" if restore_target is None else str(restore_target)
        match widget:
            case ConfigListRow():
                items = list(restore_target) if isinstance(restore_target, list) else []
                widget.set_items(items)
            case QTextEdit():
                widget.setPlainText(text)
            case QLineEdit():
                widget.setText(text)
                widget.setCursorPosition(0)

        # 本行按钮随之消失
        self.refresh()
