# src/bot/_managers/_initialization.py
"""初始化管理器（内部实现）

- 实现文件检查流程
"""

from utils.init_files import init_project_files

from ._base import BaseManager

__all__ = ["InitializationManager"]


class InitializationManager(BaseManager):
    """初始化管理器"""

    LOGGER_NAME = "Init"

    async def _execute(self) -> None:
        """加载配置进内存"""
        self._init_files()

    def _init_files(self) -> None:
        """创建必要路径"""
        self.logger.info("正在创建路径...")
        init_project_files()
