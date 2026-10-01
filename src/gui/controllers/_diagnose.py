# src/gui/controllers/_diagnose.py
"""网络诊断控制器

- 提供连通性自助排查入口
- 诊断轮驱动进程级唯一 CheckDialog，与他轮互斥不并发
"""

import asyncio

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QDialog, QWidget

from messages import CheckMessage
from utils import config_manager
from utils.diagnose import diagnose_flow
from utils.net_probe import FieldKey, FrameKey, RowId, RowStatus, verify_skeleton

from ..dialogs import (
    Round,
    current_check_window,
    open_check_window,
)
from ..mediator import gui_bridge
from ._base import BaseController

_orphans: set["_DiagnoseWorker"] = set()  # 关窗放行的线程暂养于此，finished 后自弃


class _DiagnoseWorker(QThread):
    """诊断线程

    - 异步流程每产出一帧就经信号发出
    """

    row_update = Signal(dict)  # 逐行点亮

    def __init__(
        self, configured_proxy: str, token: str, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._proxy = configured_proxy
        self._token = token

    def run(self) -> None:
        """诊断线程主循环

        - 私有事件循环驱动公共核心
        - 帧经信号 queued 回主线程
        """
        try:
            asyncio.run(
                diagnose_flow(
                    self._proxy,
                    token=self._token,
                    emit=self.row_update.emit,
                    stop_check=self.isInterruptionRequested,
                )
            )
        except Exception as e:  # 诊断自身异常也变成一行结果
            self.row_update.emit(
                {
                    "id": RowId.ADVICE,
                    "status": RowStatus.FAIL,
                    "detail": CheckMessage.SELF_CRASH.format(err=e),
                }
            )


class DiagnoseController(BaseController):
    """网络诊断控制器"""

    LOGGER_NAME = "GUI.Diagnose"
    BTN_KEY = "diagnose"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        # 启动校验结论闩锁：未出结论前拒点诊断防误判半新配置
        self._startup_settled: bool = False

        # 当前在跑的诊断线程集合：finished 前禁止被 GC
        self._workers: set[_DiagnoseWorker] = set()

        # 两条独立事件都算"启动黑盒结束"：通过转真、失败弹向导
        gui_bridge.config_ready_changed.connect(self._on_ready, "诊断刷新", queued=True)
        gui_bridge.request_force_setup.connect(
            self._settle_startup, "启动结论", queued=True
        )

    def _settle_startup(self, *_args: object) -> None:
        """启动校验结论落闩"""
        self._startup_settled = True

    # ==================== 业务逻辑实现 ====================

    def _execute(self) -> None:
        """在唯一窗上开诊断轮

        - 启动期与他轮在途一律日志拦截
        """
        if not self._startup_settled:
            self.logger.info(CheckMessage.STARTUP_BUSY)
            return

        busy = current_check_window()
        if busy is not None and busy.is_running:
            self.logger.info(CheckMessage.CHECK_BUSY)
            return

        configured = ""
        token = ""
        try:
            configured = config_manager.get("basic.proxy", str)
            token = config_manager.get("basic.telegram_token", str)
        except Exception:  # 配置未就绪按留空处理，不阻塞诊断
            pass

        # 窗出现即证据，面板不重复灌，开局整表由公共核心算好随线程首帧发出
        self.logger.debug("打开网络诊断")
        win = open_check_window(self.gui)
        win.begin_round(Round.DIAGNOSE, True, verify_skeleton(), self._on_round_closed)
        self._run(configured, token, win)

    # ==================== 轮次驱动 ====================

    def _run(self, configured: str, token: str, win: QWidget) -> None:
        """诊断轮线程启动

        - 起线程跑一轮诊断
        - 帧转发进窗
        """
        if any(w.isRunning() for w in self._workers):
            return
        worker = _DiagnoseWorker(configured, token, parent=win)
        worker.row_update.connect(lambda f: self._on_frame(f))
        worker.finished.connect(lambda w=worker: self._workers.discard(w))
        self._workers.add(worker)
        worker.start()

    def _on_frame(self, frame: dict) -> None:
        """帧转发

        - 仅诊断轮消费
        - 结论帧带断链标记则拉起强制向导
        """
        win = current_check_window()
        if win is None or win.round != Round.DIAGNOSE:
            return
        win.apply(frame)
        if (
            frame.get("id") == RowId.ADVICE
            and frame.get("status") != RowStatus.CHECKING
            and frame.get(FrameKey.BROKEN)
        ):
            gui_bridge.request_force_setup.emit({FieldKey.PROXY: frame["detail"]})

    def _on_round_closed(self, result: int) -> None:
        """窗收场

        - 进行中被中断则抛弃在跑线程
        - 单例只 hide 不销毁
        """
        if result == QDialog.DialogCode.Rejected:
            self._abandon_workers()

    def _on_ready(self, ready: bool) -> None:
        """启动通过落闩

        - 正停驻诊断轮时结论行原地刷绿
        """
        if not ready:
            return
        self._startup_settled = True
        win = current_check_window()
        if win is None or win.round != Round.DIAGNOSE or not win.settled:
            return
        win.force_apply(
            {
                "id": RowId.ADVICE,
                "status": RowStatus.OK,
                "detail": CheckMessage.VERIFIED_OK,
            }
        )

    def _abandon_workers(self) -> None:
        """抛弃在跑线程

        - 断开结果信号，摘除父级后交模块容器暂养
        """
        for worker in self._workers:
            worker.requestInterruption()
            if worker.isRunning():
                worker.setParent(None)
                _orphans.add(worker)
                worker.finished.connect(lambda w=worker: _orphans.discard(w))
                worker.finished.connect(worker.deleteLater)
        self._workers.clear()
