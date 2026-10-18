# src/gui/controllers/_verify.py
"""校验轮协调

- 驱动进程级唯一校验进度窗，校验轮之间互斥
- 维护复验与保存状态标记、待保存候选与开窗前的帧缓存
"""

from typing import TYPE_CHECKING

from skin.messages import CheckMessage
from ui import (
    CheckDialog,
    Round,
    current_check_window,
    gui_bridge,
    open_check_window,
)
from utils.config import AppConfigData
from utils.network import RowId, RowStatus, verify_skeleton

if TYPE_CHECKING:
    from ._settings import SettingsController


class VerifyCoordinator:
    """校验轮协调器

    - 与 SettingsController 一对一绑定，读取其面板与就绪缓存
    - 面板重建后重新设置从属浮窗关系
    """

    def __init__(self, host: "SettingsController") -> None:
        self._host = host

        # 复验在途标记：无落盘动作，通过只收检测窗
        self.validating: bool = False

        # 保存在途标记：本次通过时由 Qt 侧落盘候选
        self.save_pending: bool = False

        # 待落盘候选：校验通过才写入磁盘，关面板/取消即弃
        self.pending_candidate: AppConfigData | None = None

        # 迟滞开窗前的帧缓存：启动轮后台先跑，计划帧先到窗未开，开轮后补播
        self.pre_frames: list[dict] = []

    def window(self) -> CheckDialog | None:
        """取当前校验轮窗口

        - 非校验轮或无窗均返 None
        """
        win = current_check_window()
        return win if win is not None and win.round == Round.VERIFY else None

    def start_wait(self, aborts: bool) -> bool:
        """在唯一窗上开校验轮

        - 其他轮次进行中则记日志并返回 False
        - 返回是否成功打开进度窗
        """
        # 调用方据此决定是否唤醒后台
        busy = current_check_window()
        if busy is not None and busy.is_running:
            self._host.logger.info(CheckMessage.BUSY)
            self.validating = False
            self.save_pending = False
            if self._host._panel is not None:
                self._host._panel.set_busy(False)
            return False

        wait = open_check_window(self._host.gui)
        wait.begin_round(Round.VERIFY, aborts, verify_skeleton(), self.on_closed)

        # 补播迟滞期缓存的帧：计划帧带缺席结论重建表格，逐行帧按序点亮
        for frame in self.pre_frames:
            wait.apply(frame)
        self.pre_frames = []
        self.attach_transient()
        return True

    def on_closed(self, result: int) -> None:
        """窗口关闭回调

        - 校验轮进行中的 reject 视为用户中止
        """
        # 不可中断轮进行中无按钮且屏蔽 Esc，只会以 accept 收场，不动后台
        wait = self.window()
        if (
            wait is not None
            and result == wait.DialogCode.Rejected
            and not wait.settled
            and wait.aborts
        ):
            self.abort_pending()

    def abort_pending(self) -> None:
        """停止保存校验

        - 中止校验、丢弃待保存候选并解锁面板
        """
        # 保存在途走 abort 通道（Bot 中止任务并回退内存）
        if self.save_pending:
            self.pending_candidate = None
            self.save_pending = False
            self._host.logger.info(CheckMessage.VERIFY_ABORTED)
            gui_bridge.config_abort.emit()
            return

        # 复验在途无候选，只弃在途标志，被中断的校验轮收尾必发 ready，面板收到即解除忙碌
        if self.validating:
            self.validating = False
            if self._host._panel is not None:
                self._host._panel.set_busy(False)
            self._host.logger.info(CheckMessage.VERIFY_STOPPED)
            gui_bridge.config_abort.emit()

    def attach_transient(self) -> None:
        """校验窗浮在当前面板之上

        - 面板重建后需再次调用
        """
        # 本绑定无 QWidget 级接口，下到 QWindow 挂关系，句柄需 winId 强制具象
        wait = self.window()
        if wait is None:
            return
        owner = self._host._panel or self._host.gui
        wait.winId()
        owner.winId()
        wait.windowHandle().setTransientParent(owner.windowHandle())

    def on_frame(self, frame: dict) -> None:
        """进度帧转发

        - 结论帧即轮次收口，无窗轮次的缓存行帧随之作废
        - 窗口未开时先缓存，开窗后补播
        - 其他轮次占用时直接丢弃
        """
        wait = self.window()
        if wait is not None:
            wait.apply(frame)
            return
        if self._is_conclusion(frame):
            self.pre_frames = []
            return
        if current_check_window() is None:
            self.pre_frames.append(frame)

    @staticmethod
    def _is_conclusion(frame: dict) -> bool:
        """结论帧判定"""
        return frame.get("id") == RowId.ADVICE and frame.get("status") in (
            RowStatus.OK,
            RowStatus.FAIL,
        )

    def open_startup_wait(self) -> None:
        """启动校验延迟弹窗

        - 校验很快完成时不闪窗
        - 其他轮次占用时不弹
        """
        # 后台校验照跑不误，播报让路，不抢弹提示
        if self._host._config_ready or self._host._panel is not None:
            return
        busy = current_check_window()
        if busy is not None and busy.is_running:
            return
        self._host.logger.info(
            CheckMessage.VERIFY_START.format(reason=CheckMessage.REASON_STARTUP)
        )
        self.start_wait(aborts=False)
