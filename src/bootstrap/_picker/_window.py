# src/bootstrap/_picker/_window.py
"""选 bot 窗口

- 引导期选择、编辑或新建实例
"""

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app_icon import ensure_app
from messages import PickerMessage

from .._qss import build_bootstrap_qss
from .._theme import PICKER
from ._form import EditProfileDialog, NewProfileDialog
from ._store import delete_profile, list_profiles, touch_profile

# Qt 自定义数据角色，列表项各挂各的数据
_ROLE_CODE = 0x0100  # Qt.UserRole，列表项挂身份码
_ROLE_REMARK = 0x0101  # 列表项挂备注名


def _label_of(code: str, remark: str) -> str:
    """实例显示名

    - 列表行与删除确认共用同一套拼法
    """
    return f"{remark}（{code}）" if remark else code


def _sync_entries(*buttons: QPushButton, item: object) -> None:
    """按选中态联动实例级入口可用性"""
    for button in buttons:
        button.setEnabled(item is not None)


def _run_sync(button: QPushButton, dialog: "_ProfilePickerDialog") -> None:
    """弹出全局依赖管理菜单

    - 同步对象是所有实例共享的 runtime 依赖层
    """
    if not dialog._selected()[0]:
        return

    from .._plugin import open_maintain_menu

    open_maintain_menu(button, dialog)


class _ProfilePickerDialog(QDialog):
    """实例选择窗

    - 列已有实例，可启动、编辑或转入新建
    """

    def __init__(self) -> None:
        super().__init__()
        self.code = ""
        self._build()

    def _build(self) -> None:
        """装配控件"""
        self.setWindowTitle(PickerMessage.TITLE)
        self.setStyleSheet(build_bootstrap_qss())
        self.resize(PICKER.width, PICKER.height)
        self.setMinimumSize(PICKER.min_width, PICKER.min_height)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(PickerMessage.HINT))

        self._list = QListWidget()
        self._reload()
        self._list.itemDoubleClicked.connect(lambda _: self._on_start())
        layout.addWidget(self._list)

        buttons = QHBoxLayout()
        new_btn = QPushButton(PickerMessage.BTN_NEW)
        new_btn.clicked.connect(self._on_new)
        edit_btn = QPushButton(PickerMessage.BTN_EDIT)
        edit_btn.clicked.connect(self._on_edit)
        delete_btn = QPushButton(PickerMessage.BTN_DELETE)
        delete_btn.setObjectName("btn_danger")
        delete_btn.clicked.connect(self._on_delete)

        # 面板操作必须针对具体实例，空选入口置灰
        plugin_btn = QPushButton(PickerMessage.BTN_PLUGINS)
        plugin_btn.setObjectName("btn_secondary")
        plugin_btn.clicked.connect(self._on_plugins)

        sync_btn = QPushButton(PickerMessage.BTN_SYNC)
        sync_btn.setObjectName("btn_secondary")
        sync_btn.clicked.connect(lambda: _run_sync(sync_btn, self))

        # currentItemChanged 只在选中态变化时发，建钮时先按当前项定初值
        entries = (plugin_btn, sync_btn)
        self._list.currentItemChanged.connect(
            lambda cur, *_: _sync_entries(*entries, item=cur)
        )
        for entry in entries:
            entry.setEnabled(self._list.currentItem() is not None)

        start_btn = QPushButton(PickerMessage.BTN_START)
        start_btn.setObjectName("btn_start")
        start_btn.clicked.connect(self._on_start)

        # 首个入布局的按钮默认成自动默认钮，Enter会被新建抢答，显式定归启动
        start_btn.setDefault(True)

        # 左组改实例、右组走动作，中间拉伸拉开两组语义
        buttons.addWidget(new_btn)
        buttons.addWidget(edit_btn)
        buttons.addWidget(delete_btn)
        buttons.addStretch()
        buttons.addWidget(plugin_btn)
        buttons.addWidget(sync_btn)
        buttons.addWidget(start_btn)
        layout.addLayout(buttons)

    def _reload(self) -> None:
        """重建实例列表并默认选中首行"""
        self._list.clear()
        for code, remark in list_profiles():
            item = QListWidgetItem(_label_of(code, remark))
            item.setData(_ROLE_CODE, code)
            item.setData(_ROLE_REMARK, remark)
            self._list.addItem(item)
        if self._list.count():
            self._list.setCurrentRow(0)

    def _selected(self) -> tuple[str, str]:
        """取当前选中实例的身份码与备注名"""
        item = self._list.currentItem()
        if not item:
            return "", ""
        return item.data(_ROLE_CODE), item.data(_ROLE_REMARK)

    def _on_start(self) -> None:
        """启动选中实例"""
        self.code, _ = self._selected()
        if self.code:
            touch_profile(self.code)
            self.accept()

    def _on_plugins(self) -> None:
        """打开选中实例的插件面板"""
        code, _ = self._selected()
        if not code:
            return

        # 面板依赖 Qt，点击时才付出加载代价
        from .._plugin import MODE_EDIT, open_panel

        open_panel(code, MODE_EDIT)

    def _on_new(self) -> None:
        """转入新建窗，建成后回列表并选中"""
        dialog = NewProfileDialog()
        if dialog.exec() and dialog.code:
            self._reload()
            self._select_code(dialog.code)

    def _on_edit(self) -> None:
        """编辑选中实例，改完刷新列表保持选中"""
        code, remark = self._selected()
        if not code:
            return
        dialog = EditProfileDialog(code, remark)
        if dialog.exec() and dialog.code:
            self._reload()
            self._select_code(dialog.code)

    def _on_delete(self) -> None:
        """删除选中实例

        - 确认后才动手，删完刷新列表
        """
        code, remark = self._selected()
        if not code:
            return

        label = _label_of(code, remark)
        confirmed = QMessageBox.question(
            self,
            self.windowTitle(),
            PickerMessage.DELETE_CONFIRM.format(label=label),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        # 删后复查目录仍在即失败，多见于实例正在运行占用文件
        if not delete_profile(code):
            QMessageBox.warning(self, self.windowTitle(), PickerMessage.DELETE_FAIL)
            return
        self._reload()

    def _select_code(self, code: str) -> None:
        """按身份码定位并选中列表行"""
        for row in range(self._list.count()):
            if self._list.item(row).data(_ROLE_CODE) == code:
                self._list.setCurrentRow(row)
                return


def pick_profile() -> str:
    """选择或新建实例身份

    - 返回身份码，用户取消返回空串
    - 经 ensure_app 取应用实例并设置图标
    """
    ensure_app()
    dialog = _ProfilePickerDialog()
    return dialog.code if dialog.exec() else ""
