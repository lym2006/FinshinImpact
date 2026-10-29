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
from skin.messages import DialogMessage
from ui import gui_bridge
from utils.init_files import (
    PersonaSync,
    init_project_files,
    sync_persona_template,
)
from utils.lifecycle import register_lifecycle
from utils.paths import DB_BACKUP_DIR, DB_FILE
from utils.persona import applied_persona_text, load_persona_cache, read_persona_file

from ._base import BaseManager


class InitializationManager(BaseManager):
    """初始化管理器"""

    LOGGER_NAME = "Init"

    async def _execute(self) -> None:
        """建好路径再升库结构"""
        self._init_files()
        await self._migrate_database()

    def _init_files(self) -> None:
        """建好路径并按磁盘正文装填生效正文

        - 正文必须在配置应用前就位，对话身份的基准才不是空正文
        """
        self.logger.info("正在创建路径...")
        init_project_files()
        load_persona_cache()

    def sync_persona(self) -> bool:
        """人设模板对账

        - 对账可能补建过副本，按存档重装一遍才是最终正文
        - 返回正文是否自动换过新版
        """
        result = sync_persona_template()
        load_persona_cache()
        if result == PersonaSync.NOTIFY:
            gui_bridge.request_persona_update.emit()
        return result == PersonaSync.UPDATED

    def detect_external_persona(self) -> None:
        """比对实例文件与上次生效存档

        - 文件读不出即不打扰，装填那处已报过
        - 两份不一致才发信号，由界面开合一拍板窗
        """
        disk = read_persona_file()
        if disk is None:
            return
        applied = applied_persona_text()
        if disk == applied:
            return
        gui_bridge.request_persona_resolve.emit(
            applied,
            disk,
            DialogMessage.SETUP_PERSONA_LABEL_SAVED,
            DialogMessage.SETUP_PERSONA_LABEL_FILE,
        )

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
