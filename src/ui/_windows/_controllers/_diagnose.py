# src/ui/_windows/_controllers/_diagnose.py
"""网络诊断控制器

- 连通性自助排查入口
- 诊断轮驱动进程级共享的检查窗，与他轮互斥不并发
"""

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QDialog, QWidget

from finshin_sdk.domain import ConfigKey, ConfigSection, ProxyMode
from skin.messages import CheckMessage
from system.profile_env import get_profile, read_token
from utils import config_manager, get_logger
from utils.network import FrameKey, RowId, RowStatus, fault_row_of, verify_skeleton

from ..._bridge import gui_bridge
from ..._dialogs import Round, current_check_window, open_check_window
from ._base import BaseController

_logger = get_logger("GUI.Diagnose")
_orphans: set["_DiagnoseWorker"] = set()  # 关窗放行的线程暂养于此，finished 后自弃

# 一轮诊断收配置代理、token 与代理模式，逐帧回调，按停止判定中止
DiagnoseFlow = Callable[
    [str, str, str, Callable[[dict], None] | None, Callable[[], bool] | None],
    Coroutine[Any, Any, None],
]


class _DiagnoseWorker(QThread):
    """诊断线程

    - 异步流程每产出一帧就经信号发出
    """

    row_update = Signal(dict)  # 逐行点亮

    def __init__(
        self,
        configured_proxy: str,
        token: str,
        mode: str,
        flow: DiagnoseFlow,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._proxy = configured_proxy
        self._token = token
        self._mode = mode
        self._flow = flow

    def run(self) -> None:
        """诊断线程主循环

        - 私有事件循环驱动公共核心
        - 帧经信号 queued 回主线程
        """
        try:
            asyncio.run(
                self._flow(
                    self._proxy,
                    self._token,
                    self._mode,
                    self.row_update.emit,
                    self.isInterruptionRequested,
                )
            )
        except Exception:  # 诊断自身异常也变成一行结果
            _logger.debug("诊断线程异常", exc_info=True)
            self.row_update.emit(
                {
                    "id": RowId.ADVICE,
                    "status": RowStatus.FAIL,
                    "detail": CheckMessage.SELF_CRASH,
                }
            )


class DiagnoseController(BaseController):
    """网络诊断控制器"""

    LOGGER_NAME = "GUI.Diagnose"
    BTN_KEY = "diagnose"

    def __init__(self, *args, flow: DiagnoseFlow, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._flow = flow

        # 启动校验结论闩锁：未出结论前拒点诊断防误判半新配置
        self._startup_settled: bool = False

        # 代理不通时该标红哪一行，随最近一轮读的档位刷新
        self._red_key: str = fault_row_of(ProxyMode.AUTO)

        # 当前在跑的诊断线程集合：finished 前禁止被 GC
        self._workers: set[_DiagnoseWorker] = set()

        # 两条独立事件都算"启动黑盒结束"：通过转真、失败弹向导
        gui_bridge.config_ready_changed.connect(self._on_ready, "诊断刷新", queued=True)
        gui_bridge.request_force_setup.connect(
            self._settle_startup, "启动结论", queued=True
        )

    def _settle_startup(self, *_args: object) -> None:
        """标记启动校验结论已处理"""
        self._startup_settled = True

    def _execute(self) -> None:
        """在唯一窗上开诊断轮

        - 启动校验未结束或其他轮次进行中时记日志返回
        - 路线与红点行都按当前代理模式定
        """
        if not self._startup_settled:
            self.logger.info(CheckMessage.STARTUP_BUSY)
            return

        busy = current_check_window()
        if busy is not None and busy.is_running:
            self.logger.info(CheckMessage.BUSY)
            return

        proxy = config_manager.get_all().get(ConfigSection.PROXY) or {}
        configured = str(proxy.get(ConfigKey.PROXY) or "")
        mode = str(proxy.get(ConfigKey.PROXY_MODE, ProxyMode.AUTO)).strip()
        token = read_token(get_profile())

        # 窗出现即证据，面板不重复灌，开局整表由公共核心算好随线程首帧发出
        self.logger.debug("打开网络诊断")
        self._red_key = fault_row_of(mode)
        win = open_check_window(self.gui)
        win.begin_round(Round.DIAGNOSE, True, verify_skeleton(), self._on_round_closed)
        self._run(configured, token, mode, win)

    def _run(self, configured: str, token: str, mode: str, win: QWidget) -> None:
        """启动诊断线程

        - 后台跑一轮诊断，帧转发进窗口
        """
        if any(w.isRunning() for w in self._workers):
            return
        worker = _DiagnoseWorker(configured, token, mode, self._flow, parent=win)
        worker.row_update.connect(lambda f: self._on_frame(f))
        worker.finished.connect(lambda w=worker: self._workers.discard(w))
        self._workers.add(worker)
        worker.start()

    def _on_frame(self, frame: dict) -> None:
        """帧转发

        - 仅诊断轮消费
        - 结论帧带断链标记则按档位把红点交给向导
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
            gui_bridge.request_force_setup.emit({self._red_key: frame["detail"]})

    def _on_round_closed(self, result: int) -> None:
        """窗口关闭回调

        - 进行中被中断则弃用诊断线程
        - 单例只 hide 不销毁
        """
        if result == QDialog.DialogCode.Rejected:
            self._abandon_workers()

    def _on_ready(self, ready: bool) -> None:
        """启动校验通过时更新状态

        - 诊断窗停留时结论行原地更新为通过
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
        """弃用仍在运行的诊断线程

        - 断开结果信号并解除父级，移交给模块级列表防止被回收
        """
        for worker in self._workers:
            worker.requestInterruption()
            if worker.isRunning():
                worker.setParent(None)
                _orphans.add(worker)
                worker.finished.connect(lambda w=worker: _orphans.discard(w))
                worker.finished.connect(worker.deleteLater)
        self._workers.clear()
