# src/gui/dialogs/_link.py
"""断连计时弹窗

- 非模态置顶展示断线时长与重连次数
"""

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from skin.theme import GLOBAL, LINK_DIALOG
from utils.network import LinkStatus
from widgets import BaseDialog

# Qt 布局四边
_MARGIN_EDGES = 4  # setContentsMargins 收上下左右四个值


class LinkDialog(BaseDialog):
    """断连计时弹窗

    - 非模态常驻，数字由外部逐秒回写
    - 叉号只压本次断连，「本次不提示」按钮压本次运行
    """

    def __init__(
        self,
        on_close: Callable[[], None],
        on_mute: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent=parent, title=LINK_DIALOG.title)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.set_always_on_top()
        self.setStyleSheet(
            f"QDialog {{ background-color: {LINK_DIALOG.bg_color}; }}",
        )

        self._on_close = on_close

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*([LINK_DIALOG.pad] * _MARGIN_EDGES))
        layout.setSpacing(LINK_DIALOG.spacing)

        layout.addWidget(
            self._make_label(
                LINK_DIALOG.head, LINK_DIALOG.text_color, LINK_DIALOG.head_font_size
            )
        )

        self._timer = self._make_label(
            "", LINK_DIALOG.timer_color, LINK_DIALOG.timer_font_size
        )
        layout.addWidget(self._timer)

        self._retries = self._make_label(
            "", LINK_DIALOG.text_color, LINK_DIALOG.retries_font_size
        )
        layout.addWidget(self._retries)

        layout.addStretch()

        # 本次不提示按钮
        btn_layout = QHBoxLayout()
        mute_btn = self._make_button(LINK_DIALOG.mute_text, LINK_DIALOG.mute_bg)
        mute_btn.clicked.connect(lambda: self._dismiss(on_mute))
        btn_layout.addStretch()
        btn_layout.addWidget(mute_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 宽度定死，高度交内容撑开：固定高度会裁掉大字号行
        self.setFixedWidth(LINK_DIALOG.width)
        self.setFixedHeight(max(LINK_DIALOG.height, layout.sizeHint().height()))

    def refresh(self, status: LinkStatus) -> None:
        """回写断线计时与重试次数"""
        self._timer.setText(LINK_DIALOG.elapsed_fmt.format(timer=status.timer_text))
        self._retries.setText(LINK_DIALOG.retries_fmt.format(n=status.retries))

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """标题栏叉号按关闭处理"""
        event.ignore()
        self._dismiss(self._on_close)

    def _dismiss(self, callback: Callable[[], None]) -> None:
        """收起弹窗并交出后续动作"""
        self.hide()
        callback()

    def _make_button(self, text: str, bg: str) -> QPushButton:
        """构造底部按钮"""
        btn = QPushButton(text)
        btn.setFixedSize(LINK_DIALOG.btn_width, LINK_DIALOG.btn_height)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {bg}; "
            f"color: {LINK_DIALOG.btn_color}; "
            f"border-radius: {GLOBAL.radius}px; }}"
        )
        return btn

    @staticmethod
    def _make_label(text: str, color: str, font_size: int) -> QLabel:
        """构造居中文字行"""
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"color: {color};")
        label.setFont(QFont(LINK_DIALOG.font_name, font_size))
        return label
