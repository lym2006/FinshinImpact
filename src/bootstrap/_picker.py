# src/bootstrap/_picker.py
"""选 bot 窗口

- 引导期选择、编辑或新建实例
- 只依赖 Qt、profile_env 与 core.domain，不碰 utils 防路径提前冻结
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

from ._picker_form import EditProfileDialog, NewProfileDialog
from ._store import delete_profile, list_profiles, touch_profile

_WINDOW_WIDTH = 520
_WINDOW_HEIGHT = 400

# Qt 自定义数据角色，列表项各挂各的数据
_ROLE_CODE = 0x0100  # Qt.UserRole，列表项挂身份码
_ROLE_REMARK = 0x0101  # 列表项挂备注名


def _label_of(code: str, remark: str) -> str:
    """实例显示名

    - 列表行与删除确认共用同一套拼法
    """
    return f"{remark}（{code}）" if remark else code


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
        self.resize(_WINDOW_WIDTH, _WINDOW_HEIGHT)

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
        delete_btn.clicked.connect(self._on_delete)
        start_btn = QPushButton(PickerMessage.BTN_START)
        start_btn.clicked.connect(self._on_start)

        # 首个入布局的按钮默认成自动默认钮，Enter会被新建抢答，显式定归启动
        start_btn.setDefault(True)
        cancel_btn = QPushButton(PickerMessage.BTN_CANCEL)
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(new_btn)
        buttons.addWidget(edit_btn)
        buttons.addWidget(delete_btn)
        buttons.addStretch()
        buttons.addWidget(start_btn)
        buttons.addWidget(cancel_btn)
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
    - 引导锁由调用方持有，本函数只管界面
    - ensure_app 新建应用实例即挂图标，主程序 Main 复用同一个
    """
    ensure_app()
    dialog = _ProfilePickerDialog()
    return dialog.code if dialog.exec() else ""
