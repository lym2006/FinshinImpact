# src/gui/controllers/_verify.py
"""校验轮协调

- 驱动进程级唯一校验进度窗，与他轮互斥不并发
- 持有复验与保存在途标志、待落盘候选与迟滞帧缓存
"""

from typing import TYPE_CHECKING

from messages import CheckMessage
from utils.config import AppConfigData
from utils.net_probe import verify_skeleton

from ..dialogs import CheckDialog, Round, current_check_window, open_check_window
from ..mediator import gui_bridge

if TYPE_CHECKING:
    from ._settings import SettingsController


class VerifyCoordinator:
    """校验轮协调器

    - 与 SettingsController 一对一绑定，直读其面板与就绪缓存
    - 面板换装或新开后重新跟随浮顶
    """

    def __init__(self, host: "SettingsController") -> None:
        self._host = host

        # 复验在途标记：无落盘动作，通过只收检测窗
        self.validating: bool = False

        # 保存在途标记：本轮通过时由 Qt 侧落盘候选
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

        - 他轮在途则日志拦截
        - 返回是否真正开轮
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
        """唯一窗收场

        - 仅校验轮的进行中 reject 才是真停
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

        - 按钮文案即行为：中止校验、弃候选、当场解锁面板
        """
        # 保存在途走 abort 通道（Bot 中止任务并回退内存）
        if self.save_pending:
            self.pending_candidate = None
            self.save_pending = False
            self._host.logger.info(CheckMessage.VERIFY_ABORTED)
            gui_bridge.config_abort.emit()
            return

        # 复验在途无候选，只弃在途标志，被中断的校验轮收尾必发 ready，面板届时解除忙碌
        if self.validating:
            self.validating = False
            if self._host._panel is not None:
                self._host._panel.set_busy(False)
            self._host.logger.info(CheckMessage.VERIFY_STOPPED)
            gui_bridge.config_abort.emit()

    def attach_transient(self) -> None:
        """校验窗浮在当前面板之上

        - 面板换装/新开后重新跟随
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

        - 窗未开先缓存（开轮补播）
        - 他轮占用则静默丢弃
        """
        wait = self.window()
        if wait is not None:
            wait.apply(frame)
        elif current_check_window() is None:
            self.pre_frames.append(frame)

    def open_startup_wait(self) -> None:
        """启动校验迟滞弹窗

        - 快路径不闪窗
        - 他轮占用则静默让位
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
