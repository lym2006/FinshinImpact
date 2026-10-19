# src/gui/dialogs/_base.py
"""弹窗基类（内部实现）

- 定义弹窗共有样式与逻辑
- 实现全局主题统一应用
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QWidget


class BaseDialog(QDialog):
    """所有自定义弹窗的基类"""

    def __init__(self, parent: QWidget | None = None, title: str = "") -> None:
        super().__init__(parent=parent)

        self.setWindowTitle(title)  # 基础窗口属性
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
