# src/bot/_managers/_initialization.py
"""初始化管理器

- 实现文件检查、人设对账与库结构迁移
"""

from data import (
    SUPPORTED_SCHEMA,
    check_schema_compatible,
    close_all,
    get_connection,
    purge_dead_tasks,
    run_migrations,
)
from ui import gui_bridge
from utils.init_files import PersonaSync, init_project_files, sync_persona_template
from utils.lifecycle import register_lifecycle
from utils.paths import DB_BACKUP_DIR, DB_FILE
from utils.persona import reset_persona_cache

from ._base import BaseManager


class InitializationManager(BaseManager):
    """初始化管理器"""

    LOGGER_NAME = "Init"

    async def _execute(self) -> None:
        """建好路径再升库结构"""
        self._init_files()
        await self._migrate_database()

    def _init_files(self) -> None:
        """创建必要路径"""
        self.logger.info("正在创建路径...")
        init_project_files()

    def sync_persona(self) -> bool:
        """人设模板对账

        - 先清正文缓存，正文按磁盘当前内容重新组装
        - 返回正文是否自动换过新版
        """
        reset_persona_cache()
        result = sync_persona_template()
        if result == PersonaSync.UPDATED:
            self.logger.info("实例人设从未改动，已更新为最新默认人设")
            return True
        if result == PersonaSync.NOTIFY:
            self.logger.info("默认人设有更新，弹窗询问是否覆盖")
            gui_bridge.request_persona_update.emit()
        return False

    async def _migrate_database(self) -> None:
        """补做迁移并拒绝读不懂的库结构

        - 库连接打开即挂上退出清理，进程退出时合并 WAL
        """
        conn = await get_connection(DB_FILE)
        register_lifecycle(close_all, "SQLite 库连接", "hook_async")
        await run_migrations(conn, DB_FILE, DB_BACKUP_DIR)
        if not await check_schema_compatible(conn):
            raise RuntimeError(
                f"库结构版本高于本程序支持的 {SUPPORTED_SCHEMA}，请升级程序或从备份恢复"
            )
        dead = await purge_dead_tasks(conn)
        if dead:
            self.logger.info(f"中断任务判死 {dead} 个")
