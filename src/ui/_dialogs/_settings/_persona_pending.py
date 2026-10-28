# src/ui/_dialogs/_settings/_persona_pending.py
"""没保存成人设的那次取用重新拍板

- 只在启动读到取用记录时弹，运行期不读实例文件
- 关窗不算选，记录原样留着，生效正文与文件都不动
"""

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from skin.qss import build_settings_dialog_qss
from skin.theme import SETTINGS_DIALOG, ButtonStyle
from utils.init_files import drop_persona_pending
from utils.persona import applied_persona_text, pending_persona, set_draft_persona

from ..._primitives import make_button
from .._base import BaseDialog
from .._notice import NoticeDialog
from ._persona_edit import PersonaDiffDialog

# Qt 布局四边
_MARGIN_EDGES = 4  # setContentsMargins 收上下左右四个值


class PersonaPendingDialog(BaseDialog):
    """重启后的重新拍板窗

    - 左栏给当前生效那份即文件里的那份，右栏给上次没保存的那份
    - 用文件这份即抹掉记录，两边本就一致才算回到原点
    - 用上次那份即把它放进草稿，覆盖文件与换正文都等保存那一步
    """

    def __init__(self, kept: str, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, title=SETTINGS_DIALOG.persona_pending_title)

        # 没选即 None，Esc 与标题栏关闭都走这条
        self.use_kept: bool | None = None

        # 比对窗要展示的那份正文，与本窗提问读的是同一条记录
        self._kept = kept
        self.set_always_on_top()
        self.setStyleSheet(build_settings_dialog_qss())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*[SETTINGS_DIALOG.input_padding_h] * _MARGIN_EDGES)
        layout.setSpacing(SETTINGS_DIALOG.desc_spacing)
        tip = QLabel(SETTINGS_DIALOG.persona_pending_text)
        tip.setWordWrap(True)
        layout.addWidget(tip)
        layout.addLayout(self._make_buttons())

    @staticmethod
    def resolve(parent: QWidget | None = None) -> None:
        """有取用记录才问一句

        - 记录里那份跟当前生效一样即没得选，抹掉记录不打扰
        - 关窗不算选，记录留着，下次启动接着问
        - 选完的提示单独弹窗并加粗，这类选择不当场生效
        """
        pending = pending_persona()
        if pending is None:
            return
        if pending.applied == applied_persona_text():
            drop_persona_pending()
            return

        dialog = PersonaPendingDialog(pending.applied, parent=parent)
        dialog.exec()
        if dialog.use_kept is None:
            return
        if not dialog.use_kept:
            drop_persona_pending()
            NoticeDialog.notify(SETTINGS_DIALOG.persona_pending_disk_ok, parent=parent)
            return

        set_draft_persona(pending.applied)
        NoticeDialog.notify(
            SETTINGS_DIALOG.persona_pending_kept_ok,
            parent=parent,
            title=SETTINGS_DIALOG.persona_choice_title,
            bold=True,
        )

    def _make_buttons(self) -> QHBoxLayout:
        """查看变化 / 用文件这份 / 用上次那份"""
        btn_layout = QHBoxLayout()
        btn_view = make_button(SETTINGS_DIALOG.persona_view_diff, ButtonStyle.PERSONA)
        btn_view.clicked.connect(self._on_view_diff)
        btn_layout.addWidget(btn_view)
        btn_layout.addStretch()
        btn_disk = QPushButton(SETTINGS_DIALOG.persona_pending_disk_text)
        btn_disk.clicked.connect(lambda: self._choose(False))
        btn_kept = make_button(
            SETTINGS_DIALOG.persona_pending_kept_text, ButtonStyle.PRIMARY
        )
        btn_kept.clicked.connect(lambda: self._choose(True))
        btn_kept.setDefault(True)
        btn_layout.addWidget(btn_disk)
        btn_layout.addWidget(btn_kept)
        return btn_layout

    def _on_view_diff(self) -> None:
        """两栏比对当前正文与记录里那份

        - 左取文件这份，右取上次没保存的那份，与两颗按钮的取舍同序
        """
        PersonaDiffDialog.show_diff(applied_persona_text(), self._kept, parent=self)

    def _choose(self, use_kept: bool) -> None:
        """记下取舍再收窗"""
        self.use_kept = use_kept
        self.accept()
