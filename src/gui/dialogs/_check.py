# src/gui/dialogs/_check.py
"""检查进度窗（内部实现）

- 校验轮与诊断轮共用的唯一表格窗：模块级工厂保单实例，换轮原地刷
- 无×＋写死置顶：flags 首显前定死，进行中出口只有「取消」
- 不可中断轮（启动）：进行中不放按钮且屏蔽 Esc，强制跑完
"""

from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from utils.net_probe import RowId, RowStatus

from .._qss import build_check_dialog_qss
from .._theme import CHECK_DIALOG
from ._base import BaseDialog
from ._table import RowTable

__all__ = [
    "CheckDialog",
    "Round",
    "current_check_window",
    "open_check_window",
]


class Round:
    """检查窗轮次协议串：单实例上的身份标记，禁止跨模块裸写"""

    VERIFY = "verify"
    DIAGNOSE = "diagnose"


_window: "CheckDialog | None" = None  # 进程级唯一实例：谁开轮谁取，物理杜绝双窗


def open_check_window(parent: QWidget) -> "CheckDialog":
    """取得唯一检查窗：无则创建并常驻，有则原地返回"""
    global _window
    if _window is None:
        _window = CheckDialog(parent=parent)
    return _window


def current_check_window() -> "CheckDialog | None":
    """查询当前唯一实例：轮次守卫与跨控制器判空用"""
    return _window


class CheckDialog(BaseDialog):
    """检查进度表格窗（单实例，begin_round 换身份，谁开轮谁喂帧）

    - 中断轮：进行中唯一出口「取消」，点击即中断本轮交还重来
    - 不可中断轮（启动）：进行中无按钮且屏蔽 Esc，跑完才亮「知道了」
    - 成功由开轮方自动收窗，失败亮「知道了」驻留待读
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, title=CHECK_DIALOG.verify_title)
        self.setWindowModality(Qt.WindowModality.NonModal)

        # 无×＋写死置顶：×开关只在 flags 上，首显前一次性定死、终身不碰
        # 换轮换标题走 setWindowTitle，不触 flags 无重建；退出只认按钮
        flags = self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint
        self.setWindowFlags(flags | Qt.WindowType.WindowStaysOnTopHint)

        self._round: str = ""
        self._aborts = False
        self._done = False
        self._running = False
        self._on_close: Callable[[int], None] | None = None
        self._idx = 0
        self._frames = CHECK_DIALOG.spinner_frames
        self.setStyleSheet(build_check_dialog_qss())
        self.resize(CHECK_DIALOG.width, CHECK_DIALOG.height)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*[CHECK_DIALOG.pad] * 4)

        row = QHBoxLayout()
        row.setSpacing(CHECK_DIALOG.pad)
        self._spinner = QLabel(self._frames[0])
        self._spinner.setObjectName("wait_spinner")
        self._head = QLabel("")
        row.addWidget(self._spinner)
        row.addWidget(self._head)
        row.addStretch()
        layout.addLayout(row)

        self._view = RowTable(CHECK_DIALOG)
        layout.addWidget(self._view)

        self._btn = QPushButton(CHECK_DIALOG.cancel_text)
        self._btn.setObjectName("btn_primary")
        self._btn.clicked.connect(self.reject)
        # 进行中唯一出口是「取消」；不可中断轮宁可没按钮，也不给假出口
        self._btn.setVisible(False)
        layout.addWidget(self._btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._tick = QTimer(self)
        self._tick.setInterval(CHECK_DIALOG.tick_ms)
        self._tick.timeout.connect(self._advance)
        self.finished.connect(self._dispatch_close)

    def _dispatch_close(self, result: int) -> None:
        """收场分发：只回调当轮开轮方，实例常驻不销毁"""
        self._running = False
        if self._on_close is not None:
            self._on_close(result)

    def _advance(self) -> None:
        """播放下一帧转圈动画"""
        self._idx = (self._idx + 1) % len(self._frames)
        self._spinner.setText(self._frames[self._idx])

    # ==================== 轮次切换 ====================

    def begin_round(
        self,
        round_id: str,
        aborts: bool,
        rows: list[dict],
        on_close: Callable[[int], None],
    ) -> None:
        """在旧窗上原地开新一轮：换身份、换文案、复位表格与闸门

        收口后窗只是 hide、实例常驻，开轮即重新现身，调用方无需管显隐。
        on_close 承接本窗 finished：单实例下只通知当轮控制器，杜绝多方抢接信号。
        """
        self._round = round_id
        self._aborts = aborts
        self._on_close = on_close
        self._done = False
        self._running = True
        title, head, _, _ = self._texts(round_id)
        self.setWindowTitle(title)
        self._head.setText(head)
        self._view.reset(rows)
        self._spinner.setText(self._frames[0])
        self._btn.setText(CHECK_DIALOG.cancel_text)
        self._btn.setVisible(aborts)
        self._btn.clicked.disconnect()
        self._btn.clicked.connect(self.reject)
        self._tick.start()
        self.show()
        self.raise_()
        self.activateWindow()

    @staticmethod
    def _texts(round_id: str) -> tuple[str, str, str, str]:
        """按轮取（标题、进行中、成功、失败）四段文案"""
        if round_id == Round.DIAGNOSE:
            return (
                CHECK_DIALOG.diagnose_title,
                CHECK_DIALOG.diagnose_head,
                CHECK_DIALOG.diagnose_head_pass,
                CHECK_DIALOG.diagnose_head_fail,
            )
        return (
            CHECK_DIALOG.verify_title,
            CHECK_DIALOG.verify_head,
            CHECK_DIALOG.verify_head_pass,
            CHECK_DIALOG.verify_head_fail,
        )

    # ==================== 状态出口 ====================

    @property
    def round(self) -> str:
        """当前轮次：跨控制器槽的守卫依据"""
        return self._round

    @property
    def settled(self) -> bool:
        """已出结果：区分中断本轮与自动收窗的依据

        命名避开 QDialog.done()，同名 property 会被基类方法遮蔽。
        """
        return self._done

    @property
    def aborts(self) -> bool:
        """中断轮：按钮「取消」意为叫停本轮交还重来"""
        return self._aborts

    @property
    def is_running(self) -> bool:
        """一轮在途且未出结果：单实例忙碌守卫，任何新轮次此时必须让路

        收口（含失败驻留）后转 False——那时来新轮是原地覆盖重开，非并发。
        """
        return self._running

    # ==================== 帧消费 ====================

    def apply(self, frame: dict) -> None:
        """消费一帧进度：plan 整表重建，row 单行点亮，advice 结果帧收口"""
        if self._done:
            return
        self._view.apply(frame)
        if frame.get("id") == RowId.ADVICE and frame.get("status") in (
            RowStatus.OK,
            RowStatus.FAIL,
        ):
            self._finish(frame["status"] == RowStatus.OK)

    def force_apply(self, frame: dict) -> None:
        """旁路收口闸门刷单行：仅限验证通过原地转绿这类人工证据"""
        self._view.apply(frame)

    def _finish(self, passed: bool) -> None:
        """停圈亮按钮，重复调用只认首次"""
        if self._done:
            return
        self._done = True
        self._running = False
        self._tick.stop()
        _, _, pass_head, fail_head = self._texts(self._round)
        self._spinner.setText(
            CHECK_DIALOG.ok_mark if passed else CHECK_DIALOG.fail_mark
        )
        self._head.setText(pass_head if passed else fail_head)
        self._btn.setText(CHECK_DIALOG.ok_text)
        self._btn.setVisible(True)
        self._btn.clicked.disconnect()
        self._btn.clicked.connect(self.accept)

    # ==================== 进行中拦截 ====================

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """收口前屏蔽 Esc：无按钮轮的「强制」不防键盘等于没防"""
        if not self._done and event.key() == Qt.Key.Key_Escape:
            event.accept()
            return
        super().keyPressEvent(event)

    def reject(self) -> None:
        """中断关闭：取消按钮路径，先解忙再关窗"""
        self._running = False
        return super().reject()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """收口前拒关，防在途校验失去宿主"""
        if not self._done:
            event.ignore()
            return
        super().closeEvent(event)
