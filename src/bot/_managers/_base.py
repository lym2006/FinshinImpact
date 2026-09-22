# src/bot/_managers/_base.py
"""管理器基类（内部实现）

- 定义业务执行入口的统一格式
"""

from abc import ABC, abstractmethod
from typing import ClassVar

from utils import get_logger


class BaseManager(ABC):
    """Manager 基类"""

    # ==================== 契约声明区 ====================

    LOGGER_NAME: ClassVar[str]

    @abstractmethod
    async def _execute(self) -> None:
        """异步执行业务逻辑

        子类必须实现。
        """

    # ==================== 初始化与生命周期 ====================

    def __init__(self) -> None:
        self.logger = get_logger("Mgr." + self.LOGGER_NAME)

    # ==================== 公开业务执行入口 ====================

    async def execute(self) -> None:
        """统一的业务执行入口"""
        self.logger.debug(f"执行 [{self.LOGGER_NAME}]")
        await self._execute()
