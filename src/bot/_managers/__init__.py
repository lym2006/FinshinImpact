# src/bot/_managers/__init__.py
"""Bot 管理器门面

- 定义总控入口与 GUI 信号接入点
- 实现子管理器协调：初始化→校验→启动/热重载
"""

import asyncio

from utils import get_logger

from ..error_guard import error_guard
from ._apply import ConfigApplier
from ._initialization import InitializationManager
from ._service import ServiceManager
from ._settings import SettingsManager
from ._signals import SignalHandler

__all__ = ["BotManager"]


class BotManager:
    """Bot 业务管理器

    - 配置应用交 ConfigApplier，信号处理交 SignalHandler
    """

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        if hasattr(self, "_is_initialized") and self._is_initialized:
            return
        self._is_initialized = True
        self._logger = get_logger("Manager")
        self._loop = loop
        self._initializer = InitializationManager()

        # asyncio 线程私有状态
        self._shutdown = False

        # 配置应用器持有生效通道与指纹，其读取函数供引擎与校验注入子管理器
        self._applier = ConfigApplier(self)
        self._service_manager = ServiceManager(self._applier.get_config_func)
        self._settings_manager = SettingsManager(self._applier.get_raw_config_func)
        self._signals = SignalHandler(self)

    # 对外启停与信号处理，Qt 线程入口
    @error_guard("Bot 启动", catch_all=True)
    async def start(self) -> None:
        """启动服务"""
        await self._initializer.execute()
        await self._applier.apply_config()

    def on_config_saved(self) -> None:
        """配置保存回调"""
        self._loop.call_soon_threadsafe(self._signals.handle_config_saved)

    def on_config_candidate(self) -> None:
        """候选配置待验回调"""
        self._loop.call_soon_threadsafe(self._signals.handle_candidate)

    def on_config_abort(self) -> None:
        """中止在途校验回调"""
        self._loop.call_soon_threadsafe(self._signals.handle_abort)

    def on_shutdown_request(self) -> None:
        """关闭请求回调"""
        self._loop.call_soon_threadsafe(self._signals.handle_shutdown)

    def on_shutdown_cancelled(self) -> None:
        """取消关闭回调"""
        self._loop.call_soon_threadsafe(self._signals.handle_shutdown_cancel)

    def stop_service(self) -> None:
        """关闭服务并清理资源"""
        self._service_manager.stop_service()
