# src/bot/_managers/_initialization.py
"""初始化管理器

- 实现文件检查与人设对账
"""

from ui import gui_bridge
from utils.init_files import PersonaSync, init_project_files, sync_persona_template
from utils.persona import reset_persona_cache

from ._base import BaseManager


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

    def sync_persona(self) -> None:
        """人设模板对账

        - 先清正文缓存，正文按磁盘当前内容重新组装
        """
        reset_persona_cache()
        result = sync_persona_template()
        if result is PersonaSync.UPDATED:
            self.logger.info("实例人设从未改动，已更新为最新默认人设")
        elif result is PersonaSync.NOTIFY:
            self.logger.info("默认人设有更新，弹窗询问是否覆盖")
            gui_bridge.request_persona_update.emit()
