# src/ui/_dialogs/_settings/_list_widget.py
"""配置列表组件

- 字段位只挂入口行按钮，列表内容在弹窗里整体编辑
- 弹窗内列表支持双击改文本与增删
"""

from PySide6.QtCore import QModelIndex, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from skin.messages import ConfigMessage
from skin.qss import build_settings_dialog_qss, build_settings_list_qss
from skin.theme import LIST_DIALOG, SETTINGS_DIALOG, ButtonStyle, ObjectName

from ..._primitives import ThemedList, make_button
from .._base import BaseDialog

# Qt 布局四边
_MARGIN_EDGES = 4  # setContentsMargins 收上下左右四个值


class _ConfigListWidget(QWidget):
    """封装好的列表编辑控件"""

    def __init__(self, items: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(build_settings_list_qss())
        self._items = items
        self._setup_ui()

    def _setup_ui(self) -> None:
        """构建界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(*[SETTINGS_DIALOG.margin] * _MARGIN_EDGES)
        main_layout.setSpacing(SETTINGS_DIALOG.desc_spacing)
        self.list_widget = ThemedList()  # 列表区域
        self.list_widget.setObjectName(ObjectName.LIST_WIDGET)

        # 框高定死在约八行，超出走滚动条，条数少也不塌成一条缝
        self.list_widget.setFixedHeight(LIST_DIALOG.height)
        self._populate_items()

        # 连接双击编辑信号
        self.list_widget.doubleClicked.connect(self._on_double_clicked)

        # 底部工具栏 (按钮)
        main_layout.addWidget(self.list_widget)
        main_layout.addWidget(self._build_bottom_bar())

    def _populate_items(self) -> None:
        """填充初始数据"""
        for text in self._items:
            item = QListWidgetItem(str(text))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.list_widget.addItem(item)

    def _build_bottom_bar(self) -> QWidget:
        """构建底部操作栏"""
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(*[SETTINGS_DIALOG.margin] * _MARGIN_EDGES)
        layout.setSpacing(SETTINGS_DIALOG.desc_spacing)

        btn_add = make_button(ConfigMessage.LIST_ADD_TEXT, ButtonStyle.LIST_ADD)
        btn_del = make_button(ConfigMessage.LIST_DEL_TEXT, ButtonStyle.LIST_DEL)

        # 绑定逻辑
        btn_add.clicked.connect(self.add_item)
        btn_del.clicked.connect(self.remove_selected)
        layout.addWidget(btn_add)
        layout.addWidget(btn_del)
        layout.addStretch()
        return bar

    def _on_double_clicked(self, index: QModelIndex) -> None:
        """双击编辑"""
        item = self.list_widget.itemFromIndex(index)
        if item:
            self.list_widget.editItem(item)

    def add_item(self) -> None:
        """添加一项配置文本"""
        item = QListWidgetItem()
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.list_widget.addItem(item)
        self.list_widget.setCurrentItem(item)
        self.list_widget.editItem(item)

    def remove_selected(self) -> None:
        """删除选中项"""
        self.list_widget.remove_current()

    def get_values(self) -> list[str]:
        """获取非空文本值

        - 丢弃空项，防止触发词匹配全部消息
        """
        return [
            text
            for i in range(self.list_widget.count())
            if (text := self.list_widget.item(i).text().strip())
        ]


class _ConfigListDialog(BaseDialog):
    """列表项编辑弹窗

    - 由入口行按钮打开，确认才交出列表
    - 列表自带双击改文字，弹窗里点一句用法
    """

    def __init__(
        self, title: str, items: list[str], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent=parent, title=title)
        self.set_always_on_top()
        self.setStyleSheet(build_settings_dialog_qss())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*[SETTINGS_DIALOG.input_padding_h] * _MARGIN_EDGES)
        layout.setSpacing(SETTINGS_DIALOG.desc_spacing)

        self._list = _ConfigListWidget(list(items))
        layout.addWidget(self._list, stretch=1)

        tip = QLabel(ConfigMessage.LIST_EDIT_TIP)
        tip.setWordWrap(True)
        layout.addWidget(tip)

        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton(SETTINGS_DIALOG.cancel_text)
        btn_cancel.clicked.connect(self.reject)
        btn_ok = make_button(SETTINGS_DIALOG.confirm_text, ButtonStyle.PRIMARY)
        btn_ok.clicked.connect(self.accept)
        btn_ok.setDefault(True)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

    @staticmethod
    def edit(
        title: str, items: list[str], parent: QWidget | None = None
    ) -> list[str] | None:
        """模态编辑并取回列表

        - 取消返回 None
        """
        dialog = _ConfigListDialog(title, items, parent=parent)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return None
        return dialog._list.get_values()


class ConfigListRow(QWidget):
    """列表字段入口行

    - 按钮只报条数，内容改动全在弹窗里
    - 弹窗确认才回写并广播，恢复钮显隐跟着重估
    """

    # 列表内容变更信号，供恢复默认登记侧回挂
    items_changed = Signal()

    def __init__(
        self, title: str, items: list[str], parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._items = list(items)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(*[SETTINGS_DIALOG.margin] * _MARGIN_EDGES)
        layout.setSpacing(SETTINGS_DIALOG.desc_spacing)
        self._button = make_button(self._button_text(), ButtonStyle.SECONDARY)
        self._button.clicked.connect(self._on_edit)
        layout.addWidget(self._button)
        layout.addStretch()

    def get_values(self) -> list[str]:
        """取当前列表内容"""
        return list(self._items)

    def set_items(self, items: list[str]) -> None:
        """整体替换列表内容

        - 供恢复默认回填，不广播：回填方随后统一重估显隐
        """
        self._items = list(items)
        self._button.setText(self._button_text())

    def _button_text(self) -> str:
        """按钮文案，带当前条数"""
        return ConfigMessage.LIST_EDIT_TEXT.format(count=len(self._items))

    def _on_edit(self) -> None:
        """开弹窗编辑列表

        - 取消一个字不改
        """
        items = _ConfigListDialog.edit(self._title, self._items, parent=self.window())
        if items is None:
            return
        self._items = items
        self._button.setText(self._button_text())
        self.items_changed.emit()
