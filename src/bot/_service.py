# src/bot/_service.py
"""Bot 服务（内部实现）

- 实现后台线程中的 asyncio 事件循环
- 提供自动重连与日志记录的轮询
"""

import asyncio
import shutil
import threading

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramNetworkError
from tenacity import (
    RetryCallState,
    retry,
    stop_after_delay,
    wait_exponential,
)

from gui.mediator import gui_bridge
from utils import TEMP_DIR, get_logger, register_lifecycle, unregister_lifecycle


def _retry_if_network_running(state: RetryCallState) -> bool:
    """判定是否需要重连"""
    if state.outcome is None or not state.outcome.failed:
        return False
    # outcome 是 Future，用 exception() 取异常
    exc = state.outcome.exception()
    return isinstance(exc, TelegramNetworkError) and not state.args[0].is_stopping


_RECONNECT_TIMEOUT = 60
_MIN_RETRY_DELAY = 1
_MAX_RETRY_DELAY = 10

_logger = get_logger("Service")


class BotService:
    """服务线程一体化引擎"""

    def __init__(self, bot: Bot, dispatcher: Dispatcher) -> None:
        self._bot = bot
        self._dispatcher = dispatcher
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ==================== 对外接口 ====================

    @property
    def is_running(self) -> bool:
        """服务线程是否存活"""
        return self._thread is not None and self._thread.is_alive()

    @property
    def is_stopping(self) -> bool:
        """是否收到停止指令"""
        return self._stop_event.is_set()

    def start(self) -> None:
        """后台线程 + 轮询"""
        if self._thread and self._thread.is_alive():
            _logger.error("引擎启动失败: 已在运行")
            return

        _logger.info("正在启动引擎...")
        self._stop_event.clear()
        ready = threading.Event()
        self._thread = threading.Thread(
            target=self._run_loop, args=(ready,), name="BotService", daemon=True
        )
        register_lifecycle(target=self._thread, desc="BotService", type_="thread")
        self._thread.start()

        # 阻塞等待 loop 创建完成，超时保护
        if not ready.wait(timeout=5.0):
            raise RuntimeError("BotService event loop 启动超时")
        _logger.debug("引擎线程已运行")

    def stop(self) -> None:
        """停止轮询并关闭循环"""
        if not self._thread or not self._thread.is_alive():
            return

        _logger.debug("正在收尾资源...")
        self._stop_event.set()

        if self._loop and not self._loop.is_closed():
            try:
                # stop_polling 是协程，必须投递到 loop 中 await 执行；
                # call_soon_threadsafe 只能调度同步回调，直接传协程函数
                # 会产生"从未 await 的协程对象"警告且不会真正停止轮询
                asyncio.run_coroutine_threadsafe(
                    self._dispatcher.stop_polling(), self._loop
                )
                # polling 停止后收尾关闭 loop（轮询协程退出时自行处理）
            except RuntimeError:
                pass

        gui_bridge.shutdown_completed_event.set()
        _logger.debug("服务已停止")

    # ==================== 内部实现 ====================

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
            try:
                self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            except Exception:
                pass
            self._loop.close()
            self._loop = None

    async def _polling_task(self) -> None:
        """执行自动重连轮询"""
        self._temp_hook = lambda: shutil.rmtree(TEMP_DIR, ignore_errors=True)
        register_lifecycle(self._bot.session.close, "Telegram Session", "hook_async")
        register_lifecycle(self._temp_hook, "临时目录", "hook_sync")

        try:
            await self._start_polling()
        except asyncio.CancelledError:
            _logger.debug("轮询被取消")
        finally:
            # 只清自己并按对象注销：全局 shutdown_all 留给进程退出，
            # 热重载时旧服务不再动注册表（顺序混乱与互踩的根因）
            try:
                await self._bot.session.close()
            except Exception as e:
                _logger.send_error("关闭 Session 失败", e)
            self._temp_hook()
            unregister_lifecycle(self._bot.session.close, "hook_async")
            unregister_lifecycle(self._temp_hook, "hook_sync")
            unregister_lifecycle(self._thread, "thread")

    @retry(
        retry=_retry_if_network_running,
        stop=stop_after_delay(_RECONNECT_TIMEOUT),
        wait=wait_exponential(min=_MIN_RETRY_DELAY, max=_MAX_RETRY_DELAY),
        before_sleep=lambda retry_state: _logger.error(
            f"机器人断开连接，准备第 {retry_state.attempt_number} 次重连..."
        ),
        reraise=True,
    )
    async def _start_polling(self) -> None:
        """启动轮询任务"""
        _logger.info("正在启动轮询...")
        try:
            await self._dispatcher.start_polling(self._bot)
        except asyncio.CancelledError:
            _logger.info("轮询被外部取消")
        finally:
            _logger.debug("轮询已停止")
