# src/bot/_managers/_initialization.py
"""初始化管理器

- 实现文件检查流程
"""

from skin.messages import MiscMessage
from ui import gui_bridge
from utils.init_files import PersonaSync, init_project_files, sync_persona_template

from ._base import BaseManager


class InitializationManager(BaseManager):
    """初始化管理器"""

    LOGGER_NAME = "Init"

    async def _execute(self) -> None:
        """加载配置进内存"""
        self._init_files()
        self._sync_persona()

    def _init_files(self) -> None:
        """创建必要路径"""
        self.logger.info("正在创建路径...")
        init_project_files()

    def _sync_persona(self) -> None:
        """人设模板对账"""
        result = sync_persona_template()
        if result is PersonaSync.UPDATED:
            self.logger.info("实例人设从未改动，已更新为最新默认人设")
        elif result is PersonaSync.NOTIFY:
            self.logger.info("默认人设有更新，弹窗提示手动处理")
            gui_bridge.request_notice.emit(MiscMessage.PERSONA_OUTDATED, False)
