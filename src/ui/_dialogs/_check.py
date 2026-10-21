# src/ui/_dialogs/_check.py
"""检查进度窗

- 校验轮与诊断轮共用的唯一表格窗，换轮原地重置
- 窗口置顶在首显前定死，进行中只留「取消」出口
- 启动轮进行中无按钮并屏蔽 Esc，跑完才结束
"""

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from skin.qss import build_check_dialog_qss
from skin.theme import CHECK_DIALOG, ButtonStyle, ObjectName
from utils.network import FrameKey, RowId, RowStatus

from .._lifecycle import Ticker
from .._primitives import make_button
from ._base import BaseDialog
from ._table import RowTable

# Qt 布局四边
_MARGIN_EDGES = 4  # setContentsMargins 收上下左右四个值


class Round:
    """检查窗轮次协议串

    - 单实例上的身份标记，禁止跨模块裸写
    """

    VERIFY = "verify"
    DIAGNOSE = "diagnose"


_window: "CheckDialog | None" = None  # 进程级唯一实例：谁开轮谁取，物理杜绝双窗


def open_check_window(parent: QWidget) -> "CheckDialog":
    """取得唯一检查窗

    - 无则创建并常驻，有则原地返回
    """
    global _window
    if _window is None:
        _window = CheckDialog(parent=parent)
    return _window


def current_check_window() -> "CheckDialog | None":
    """查询当前唯一实例

    - 轮次守卫与跨控制器判空用
    """
    return _window


class CheckDialog(BaseDialog):
    """检查进度表格窗

    - 单实例按轮次续用，进度帧由发起方传入
    - 中断轮进行中只有「取消」，点击即中断当轮
    - 启动轮进行中无按钮并屏蔽 Esc，跑完显示「知道了」
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent, title=CHECK_DIALOG.verify_title)
        self.setWindowModality(Qt.WindowModality.NonModal)

        # ×开关只在 flags 上，首显前定死，换轮换标题不触 flags 无重建，退出只认按钮
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

        # 宽度定死、高度交给布局最小值：表格随行数收紧，默认尺寸即最小尺寸
        self.setFixedWidth(CHECK_DIALOG.width)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(*[CHECK_DIALOG.pad] * _MARGIN_EDGES)

        row = QHBoxLayout()
        row.setSpacing(CHECK_DIALOG.pad)
        self._spinner = QLabel(self._frames[0])
        self._spinner.setObjectName(ObjectName.WAIT_SPINNER)
        self._head = QLabel("")
        row.addWidget(self._spinner)
        row.addWidget(self._head)
        row.addStretch()
        layout.addLayout(row)

        self._view = RowTable(CHECK_DIALOG)
        layout.addWidget(self._view)

        self._btn = make_button(CHECK_DIALOG.cancel_text, ButtonStyle.PRIMARY)
        self._btn.clicked.connect(self.reject)

        # 进行中唯一出口是「取消」，不可中断轮宁可没按钮，也不给假出口
        self._btn.setVisible(False)
        layout.addWidget(self._btn, alignment=Qt.AlignmentFlag.AlignRight)

        self._tick = Ticker(self, CHECK_DIALOG.tick_ms, self._advance)
        self.finished.connect(self._dispatch_close)

    def _dispatch_close(self, result: int) -> None:
        """关闭后分发

        - 只回调本次发起方，实例常驻不销毁
        """
        self._running = False
        if self._on_close is not None:
            self._on_close(result)

    def _advance(self) -> None:
        """播放下一帧转圈动画"""
        self._idx = (self._idx + 1) % len(self._frames)
        self._spinner.setText(self._frames[self._idx])

    def begin_round(
        self,
        round_id: str,
        aborts: bool,
        rows: list[dict],
        on_close: Callable[[int], None],
    ) -> None:
        """原地开启新一轮

        - 重置轮次、文案、表格与结束状态
        - 窗口隐藏后发起新一轮会自动重新显示
        - 关闭回调只通知本次发起方
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

        # 模态在演则让位：同档 raise 只插队，会把抓握输入的确认框重新盖没
        if QApplication.activeModalWidget() is None:
            self.raise_()
            self.activateWindow()

    @staticmethod
    def _texts(round_id: str) -> tuple[str, str, str, str]:
        """按轮取四段文案

        - 依次为标题、进行中、成功、失败
        """
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

    @property
    def round(self) -> str:
        """当前轮次

        - 控制器据此判别窗口归属
        """
        return self._round

    @property
    def settled(self) -> bool:
        """已出结果

        - 据此区分用户中断与正常结束
        """
        return self._done

    @property
    def aborts(self) -> bool:
        """中断轮"""
        return self._aborts

    @property
    def is_running(self) -> bool:
        """一轮进行中且未出结果

        - 为真时新轮次必须等待或放弃
        """
        return self._running

    def apply(self, frame: dict) -> None:
        """消费一帧进度

        - rows 帧整表重建，id 帧更新单行，结论帧结束当轮
        - head 键换头部提示，结束文案落地时覆写回成败句
        """
        if self._done:
            return
        if frame.get(FrameKey.HEAD):
            self._head.setText(frame[FrameKey.HEAD])
        self._view.apply(frame)
        if frame.get("id") == RowId.ADVICE and frame.get("status") in (
            RowStatus.OK,
            RowStatus.FAIL,
        ):
            self._finish(frame["status"] == RowStatus.OK)

    def force_apply(self, frame: dict) -> None:
        """绕过结束状态直接更新单行

        - 仅用于验证通过后原地更新为通过
        """
        self._view.apply(frame)

    def _finish(self, passed: bool) -> None:
        """停止动画并显示结果按钮

        - 重复调用只认首次
        """
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

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """结果未出时屏蔽 Esc

        - 防止键盘绕过无按钮轮的约束
        """
        if not self._done and event.key() == Qt.Key.Key_Escape:
            event.accept()
            return
        super().keyPressEvent(event)

    def reject(self) -> None:
        """中断关闭

        - 取消按钮走此路径，先复位运行标志再关窗
        """
        self._running = False
        return super().reject()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """结果未出时拒绝关闭

        - 防止探测任务失去窗口宿主
        """
        if not self._done:
            event.ignore()
            return
        super().closeEvent(event)
