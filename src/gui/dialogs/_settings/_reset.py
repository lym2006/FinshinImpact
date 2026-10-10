# src/gui/dialogs/_settings/_reset.py
"""恢复默认登记

- 按控件当前值重估恢复按钮显隐
- 回填目标值并刷新显隐
"""

from collections.abc import Callable
from typing import TypeAlias

from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QWidget,
)

from utils.config.models import ConfigValue, FieldSchema

from ..._theme import SETTINGS_DIALOG
from ._list_widget import ConfigListWidget

InputWidget: TypeAlias = ConfigListWidget | QLineEdit | QTextEdit | QCheckBox
Inputs: TypeAlias = dict[str, InputWidget]


# Qt 布局四边
_MARGIN_EDGES = 4  # setContentsMargins 收上下左右四个值


class ResetRegistry:
    """恢复默认登记

    - 按控件当前值重估按钮显隐并回填
    """

    def __init__(
        self,
        inputs: Inputs,
        value_of: Callable[[str, FieldSchema], ConfigValue],
    ) -> None:
        self._inputs = inputs
        self._value_of = value_of

        # {字段键: (按钮, 字段, 恢复目标)}
        self._rows: dict[str, tuple[QPushButton, FieldSchema, ConfigValue]] = {}

    def wrap(
        self, widget: QWidget, field_key: str, restore_target: ConfigValue
    ) -> tuple[QWidget, QPushButton]:
        """输入控件右侧挂恢复按钮"""
        # 图标态，悬停出提示
        row = QWidget()
        h_layout = QHBoxLayout(row)
        h_layout.setContentsMargins(*[SETTINGS_DIALOG.margin] * _MARGIN_EDGES)
        h_layout.setSpacing(SETTINGS_DIALOG.desc_spacing)
        h_layout.addWidget(widget, stretch=1)
        btn = QPushButton(SETTINGS_DIALOG.reset_icon)
        btn.setObjectName("btn_reset")
        btn.setToolTip(SETTINGS_DIALOG.reset_text)

        # 恢复只回填控件：落盘仍走正常保存链路，diff 窗就是唯一确认点
        btn.clicked.connect(lambda: self.reset(field_key, restore_target))
        h_layout.addWidget(btn)
        return row, btn

    def register(
        self,
        btn: QPushButton,
        field_key: str,
        field: FieldSchema,
        restore_target: ConfigValue,
    ) -> None:
        """登记恢复按钮

        - 初始隐藏
        """
        # 显隐统一交给刷新时机判定
        btn.setVisible(False)
        self._rows[field_key] = (btn, field, restore_target)

    def refresh(self) -> None:
        """重估全部恢复按钮显隐

        - 面板打开与校验回传时各刷一次
        """
        # 判定对象是控件里的当前值而非磁盘快照，手改待保存的偏离同样亮钮
        for field_key, (btn, field, restore_target) in self._rows.items():
            btn.setVisible(self._value_of(field_key, field) != restore_target)

    def reset(self, field_key: str, restore_target: ConfigValue) -> None:
        """按控件类型回填恢复目标值

        - 回填即等于默认：重估显隐
        """
        # 本行按钮随之消失
        widget = self._inputs.get(field_key)
        if widget is None:
            return
        text = "" if restore_target is None else str(restore_target)
        match widget:
            case ConfigListWidget():
                items = list(restore_target) if isinstance(restore_target, list) else []
                widget.set_items(items)
            case QCheckBox():
                widget.setChecked(bool(restore_target))
            case QTextEdit():
                widget.setPlainText(text)
            case QLineEdit():
                widget.setText(text)
        self.refresh()
