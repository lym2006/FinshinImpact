# src/bot/_managers/_initialization.py
"""初始化管理器（内部实现）

- 实现文件检查与版本检测流程
"""

from exceptions import MAPS, VersionError
from utils import check_updates
from utils.init_files import init_project_files

from ._base import BaseManager

_ERR_MAP_VERSION = MAPS["Init"]["Version"]


class InitializationManager(BaseManager):
    """初始化管理器"""

    LOGGER_NAME = "Init"

    async def _execute(self) -> None:
        """文件检查后执行版本检测"""
        self._init_files()
        await self._check_version()

    def _init_files(self) -> None:
        """创建必要路径"""
        self.logger.info("正在创建路径...")
        init_project_files()

    async def _check_version(self) -> None:
        """检查最新版本"""
        self.logger.info("正在检查版本...")
        try:
            ver = await check_updates()
            self.logger.info(f"版本检查通过：{ver}")
        except VersionError as e:
            self.logger.send_error(_ERR_MAP_VERSION[type(e)].format(**vars(e)), e)
