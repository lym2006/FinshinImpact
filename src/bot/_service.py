# src/bot/_service.py
"""Bot 服务

- 实现后台线程中的 asyncio 事件循环
- 托管轮询的启停与日志记录
- 托管插件常驻协程的起停
"""

import asyncio
import threading
from typing import TYPE_CHECKING

from core.domain import PluginBackground
from skin.messages import EngineMessage
from utils import get_logger, register_lifecycle, unregister_lifecycle
from utils.network import link_report

if TYPE_CHECKING:
    from adapters.telegram.adapter import TelegramAdapter


# 引擎线程握手
_LOOP_READY_TIMEOUT = 5.0  # 等事件循环线程就绪最多 5 秒
_POLL_RETRY_DELAY = 3.0  # 起轮询撞上链路故障后的退避秒数
_BACKGROUND_STOP_TIMEOUT = 2.0  # 等插件常驻协程收拢最多 2 秒
_IDLE_WAIT_TIMEOUT = 3.0  # 等引擎收尾跑完最多 3 秒

_logger = get_logger("Service")


class BotService:
    """Bot 服务线程"""

    def __init__(
        self,
        adapter: "TelegramAdapter",
        backgrounds: tuple[PluginBackground, ...] = (),
    ) -> None:
        self._adapter = adapter
        self._backgrounds = backgrounds
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._idle_event = threading.Event()

    @property
    def is_running(self) -> bool:
        """服务线程是否存活"""
        return self._thread is not None and self._thread.is_alive()

    @property
    def is_stopping(self) -> bool:
        """是否收到停止指令"""
        return self._stop_event.is_set()

    def start(self) -> None:
        """启动服务线程"""
        if self._thread and self._thread.is_alive():
            _logger.error(EngineMessage.ALREADY_RUNNING)
            return

        _logger.info(EngineMessage.STARTING)
        self._stop_event.clear()
        self._idle_event.clear()
        ready = threading.Event()
        self._thread = threading.Thread(
            target=self._run_loop, args=(ready,), name="BotService", daemon=True
        )
        register_lifecycle(target=self._thread, desc="BotService", type_="thread")
        self._thread.start()

        # 阻塞等待 loop 创建完成，超时保护
        if not ready.wait(timeout=_LOOP_READY_TIMEOUT):
            raise RuntimeError("BotService event loop 启动超时")
        _logger.debug("引擎线程已运行")

    def stop(self) -> None:
        """停止轮询并等引擎收尾

        - 取消与收拢都跑在引擎线程，本线程限时等它挂上收尾完成旗
        """
        if not self._thread or not self._thread.is_alive():
            self._idle_event.set()
            return

        _logger.debug("正在收尾资源...")
        self._stop_event.set()
        link_report.reset()

        if self._loop and not self._loop.is_closed():
            try:
                # stop_polling 是协程：threadsafe 投递才会 await，同步调度传协程不会真停
                asyncio.run_coroutine_threadsafe(self._adapter.stop(), self._loop)

                # polling 停止后收尾关闭 loop（轮询协程退出时自行处理）
            except RuntimeError:
                pass

        if not self._idle_event.wait(timeout=_IDLE_WAIT_TIMEOUT):
            _logger.error(f"引擎收尾未在 {_IDLE_WAIT_TIMEOUT} 秒内完成")
        _logger.debug("服务已停止")

    def _run_loop(self, ready: threading.Event) -> None:
        """后台线程入口"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        ready.set()  # 通知主线程 loop 已就绪

        try:
            self._loop.run_until_complete(self._polling_task())
        except RuntimeError as e:
            # stop() 里 loop.stop() 属正常收尾，不是故障
            if "stopped before Future completed" not in str(e):
                _logger.send_error("BotService loop 异常", e)
        except Exception as e:
            _logger.send_error("BotService loop 异常", e)
        finally:
            link_report.reset()  # 线程收尾即作废断连周期，防弹窗挂着走表
            try:
                self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            except Exception:
                pass
            self._loop.close()
            self._loop = None

    async def _polling_task(self) -> None:
        """执行自动重连轮询

        - 常驻协程与轮询同一条命，退出路径统一在 finally 收
        """
        register_lifecycle(
            self._adapter.bot.session.close, "Telegram Session", "hook_async"
        )
        tasks = [asyncio.create_task(hook()) for hook in self._backgrounds]

        try:
            await self._start_polling()
        except asyncio.CancelledError:
            _logger.debug("轮询被取消")
        finally:
            await self._stop_backgrounds(tasks)

            # 只清自己并按对象注销：全局清理留给进程退出，防热重载互踩注册表
            try:
                await self._adapter.bot.session.close()
            except Exception as e:
                _logger.send_error("关闭 Session 失败", e)
            unregister_lifecycle(self._adapter.bot.session.close, "hook_async")
            unregister_lifecycle(self._thread, "thread")
            self._idle_event.set()

    async def _stop_backgrounds(self, tasks: list[asyncio.Task]) -> None:
        """收掉插件常驻协程

        - 取消后限时等待，超时即放行，穿透出来的异常按原样记录，不外抛
        """
        if not tasks:
            return
        for task in tasks:
            task.cancel()
        _, pending = await asyncio.wait(tasks, timeout=_BACKGROUND_STOP_TIMEOUT)
        if pending:
            _logger.error(f"插件后台协程未在 {_BACKGROUND_STOP_TIMEOUT} 秒内收拢")
        for task in tasks:
            if task.cancelled() or not task.done():
                continue
            error = task.exception()
            if isinstance(error, Exception):
                _logger.send_error("插件后台协程出错", error)

    async def _start_polling(self) -> None:
        """启动轮询任务

        - 链路故障时退避重试到连上或收到停服，非链路异常外抛
        """
        from adapters.telegram.session import is_link_failure

        _logger.info(EngineMessage.POLLING_START)
        try:
            while not self._stop_event.is_set():
                try:
                    await self._adapter.start()
                    return
                except asyncio.CancelledError:
                    _logger.info(EngineMessage.POLLING_CANCELLED)
                    return
                except Exception as exc:
                    if not is_link_failure(exc):
                        raise
                    if await asyncio.to_thread(
                        self._stop_event.wait, _POLL_RETRY_DELAY
                    ):
                        return
        finally:
            _logger.debug("轮询已停止")
