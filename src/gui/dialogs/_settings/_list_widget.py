# src/gui/dialogs/_settings/_list_widget.py
"""配置列表组件

- 定义标签页内的字段列表布局
- 提供恢复默认所需的整体重置与按钮挂载口
"""

from collections.abc import Callable

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..._qss import build_settings_list_qss
from ..._theme import SETTINGS_DIALOG

# Qt 布局四边
_MARGIN_EDGES = 4  # setContentsMargins 收上下左右四个值


class ConfigListWidget(QWidget):
    """封装好的列表配置控件"""

    def __init__(
        self, items: list[str], description: str = "", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet(build_settings_list_qss())
        self._items = items
        self._desc_text = description
        self._setup_ui()

    def _setup_ui(self) -> None:
        """构建界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(*[SETTINGS_DIALOG.margin] * _MARGIN_EDGES)
        main_layout.setSpacing(SETTINGS_DIALOG.desc_spacing)
        self.list_widget = QListWidget()  # 列表区域
        self.list_widget.setObjectName("list_widget")
        self._populate_items()

        # 连接双击编辑信号
        self.list_widget.doubleClicked.connect(self._on_double_clicked)

        # 底部工具栏 (描述 + 按钮)
        bottom_bar = self._build_bottom_bar()
        main_layout.addWidget(self.list_widget)
        main_layout.addWidget(bottom_bar)

    def _populate_items(self) -> None:
        """填充初始数据"""
        for text in self._items:
            item = QListWidgetItem(str(text))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
            self.list_widget.addItem(item)

    def _build_bottom_bar(self) -> QWidget:
        """构建底部操作栏

        - 布局留引用：恢复默认按钮由调用方事后挂入
        """
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(*[SETTINGS_DIALOG.margin] * _MARGIN_EDGES)
        layout.setSpacing(SETTINGS_DIALOG.desc_spacing)
        self._bar_layout = layout

        # 描述文字
        if self._desc_text:
            label = self._create_desc_label(self._desc_text)
            layout.addWidget(label, stretch=1)

        btn_add = QPushButton("添加新项")  # 按钮
        btn_del = QPushButton("删除选中")

        # 绑定样式名
        btn_add.setObjectName("btn_list_add")
        btn_del.setObjectName("btn_list_del")

        # 绑定逻辑
        btn_add.clicked.connect(self.add_item)
        btn_del.clicked.connect(self.remove_selected)
        layout.addWidget(btn_add)
        layout.addWidget(btn_del)
        return bar

    def _create_desc_label(self, text: str) -> QLabel:
        """创建说明标签"""
        label = QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return label

    def _on_double_clicked(self, index: QModelIndex) -> None:
        """双击编辑"""
        item = self.list_widget.itemFromIndex(index)
        if item:
            self.list_widget.editItem(item)

    def add_item(self) -> None:
        """外部可调用的添加逻辑"""
        item = QListWidgetItem()
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.list_widget.addItem(item)
        self.list_widget.setCurrentItem(item)
        self.list_widget.editItem(item)

    def remove_selected(self) -> None:
        """外部可调用的删除逻辑"""
        row = self.list_widget.currentRow()
        if row >= 0:
            self.list_widget.takeItem(row)

    def get_values(self) -> list[str]:
        """获取非空文本值

        - 空项丢弃
        - 防触发词误命中全部消息
        """
        return [
            text
            for i in range(self.list_widget.count())
            if (text := self.list_widget.item(i).text().strip())
        ]

    def set_items(self, items: list[str]) -> None:
        """整体替换列表内容

        - 恢复默认专用：清空后按新列表重建行
        """
        self.list_widget.clear()
        self._items = items
        self._populate_items()

    def add_reset_button(
        self, icon: str, tooltip: str, on_click: Callable[[], None]
    ) -> QPushButton:
        """底栏追加恢复默认按钮

        - 图标态，悬停出提示
        """
        btn = QPushButton(icon)
        btn.setObjectName("btn_reset")
        btn.setToolTip(tooltip)
        btn.clicked.connect(on_click)
        self._bar_layout.addWidget(btn)
        return btn
