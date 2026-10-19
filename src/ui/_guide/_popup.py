# src/ui/_guide/_popup.py
"""引导期提示弹窗

- 资格判定失败就地弹窗，图标按严重度切换
"""

from PySide6.QtWidgets import QMessageBox

from skin.qss import build_bootstrap_qss

from .._lifecycle import ensure_app


def show_popup(title_text: str, body: str, *, icon_warning: bool = True) -> None:
    """模态弹出提示框"""
    ensure_app()
    box = QMessageBox()
    box.setStyleSheet(build_bootstrap_qss())
    box.setIcon(
        QMessageBox.Icon.Warning if icon_warning else QMessageBox.Icon.Information
    )
    box.setWindowTitle(title_text)
    box.setText(body)
    box.exec()
