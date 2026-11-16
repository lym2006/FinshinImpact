"""引导期提示弹窗

- 资格判定失败就地弹窗，图标按严重度切换
- 按钮文字一律取弹窗文案表，二次确认默认停在否
"""

from PySide6.QtWidgets import QMessageBox, QWidget

from skin.messages import DialogMessage
from skin.qss import build_bootstrap_qss
from skin.theme import NOTICE_DIALOG

from .._lifecycle import ensure_app


def confirm_popup(title_text: str, body: str, parent: QWidget | None = None) -> bool:
    """模态二次确认，默认按钮停在否"""
    box = _box(title_text, body, QMessageBox.Icon.Question, parent)
    yes = box.addButton(DialogMessage.CONFIRM_YES, QMessageBox.ButtonRole.AcceptRole)
    no = box.addButton(DialogMessage.CONFIRM_NO, QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(no)
    box.exec()

    return box.clickedButton() is yes


def show_popup(
    title_text: str,
    body: str,
    *,
    icon_warning: bool = True,
    parent: QWidget | None = None,
) -> None:
    """模态弹出一句提示，只给一只「知道了」"""
    icon = QMessageBox.Icon.Warning if icon_warning else QMessageBox.Icon.Information
    box = _box(title_text, body, icon, parent)
    box.addButton(DialogMessage.NOTICE_OK, QMessageBox.ButtonRole.AcceptRole)
    box.exec()


def _box(
    title_text: str, body: str, icon: QMessageBox.Icon, parent: QWidget | None = None
) -> QMessageBox:
    """装配一只不带按钮的提示窗，按钮由调用处点名"""
    ensure_app()
    box = QMessageBox(parent)
    box.setStyleSheet(build_bootstrap_qss())
    box.setIcon(icon)
    box.setStandardButtons(QMessageBox.StandardButton.NoButton)
    box.setWindowTitle(title_text)

    # 长正文由 QMessageBox 自己按屏宽折，这里只钉住别被短句收成一根细条
    box.setMinimumWidth(NOTICE_DIALOG.width)
    box.setText(body)

    return box
