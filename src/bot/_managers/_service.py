# src/bot/_managers/_service.py
"""服务管理器（内部实现）

- 实现 BotService 生命周期管理
- 提供组件构建与停止清理入口
"""

import asyncio
from collections.abc import Callable

from aiogram import Bot, Dispatcher

from utils.middleware import LoggingMiddleware
from utils.plugins_register import register_routers
from utils.ssl import SSLUnverifiedSession

from .._service import BotService
from ._base import BaseManager


class ServiceManager(BaseManager):
    """服务管理器"""

    LOGGER_NAME = "Service"

    def __init__(
        self,
        get_config_func: Callable[[], tuple[str, str]],
    ) -> None:
        super().__init__()
        self._get_config = get_config_func
        self._service: BotService | None = None

    async def _execute(self) -> None:
        """启动 Bot 服务"""
        self.stop_service()  # 停掉旧服务（如果有）

        self.logger.info("正在创建引擎...")
        bot, dispatcher = self._create_components()
        self._service = BotService(bot, dispatcher)

        await asyncio.to_thread(self._service.start)
        self.logger.info("引擎启动成功")

    def _create_components(self) -> tuple[Bot, Dispatcher]:
        """按配置构建 Bot 与分发器"""
        token, proxy = self._get_config()
        bot = Bot(token=token, session=SSLUnverifiedSession(proxy=proxy))
        dispatcher = Dispatcher()

        # 注册中间件和路由（守卫注册在外层日志之后，兜底所有下游异常）
        dispatcher.update.outer_middleware(LoggingMiddleware())
        report = register_routers(dispatcher)
        total = len(report)
        self.logger.info(f"插件注册完成，共 {total} 项")
        for index, (name, ok, reason) in enumerate(report, 1):
            if ok:
                self.logger.info(f"[{index}/{total}] 插件 {name} 注册成功")
            else:
                self.logger.error(f"[{index}/{total}] 插件 '{name}' {reason}")

        return bot, dispatcher

    def stop_service(self) -> None:
        """停止 Bot 服务"""
        if not self._service:
            return
        self.logger.info("正在停止引擎...")
        service = self._service
        self._service = None
        service.stop()
