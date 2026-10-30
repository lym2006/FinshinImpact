# src/plugins/AI/services/_receipt.py
"""停机交代服务

- 实现重启时对欠答问答的逐主体补说
- 说完才结算这批任务行
"""

from core.contracts import InteractionPort
from core.domain import ContentKind
from core.dto import OutboundPayloadDTO
from data import build_repositories, get_connection, purge_dead_tasks
from utils import get_logger
from utils.paths import DB_FILE

from ..._shared.messages import BotMessage

_logger = get_logger("Plg.AI.Receipt")

# 交代句式，按主体轮换，同群连着说也不至于一个字不差
_LOST_LINES = (BotMessage.CHAT_LOST_SLEEP, BotMessage.CHAT_LOST_LINK)


async def report_lost_tasks(interaction: InteractionPort) -> None:
    """引擎开跑前把停机期间欠下的问答补一句

    - 库里一行活账即一个主体欠的一串，逐行各说一句，不判权限
    - 没欠账即一句不说，判死也不跑
    - 送不出去的记进面板，整批照旧判死，防下次启动重说一遍
    """
    conn = await get_connection(DB_FILE)
    rows = await build_repositories(conn).task.list_all_unfinished()
    if not rows:
        return

    for index, task in enumerate(rows):
        line = _LOST_LINES[index % len(_LOST_LINES)]
        try:
            payload = OutboundPayloadDTO(kind=ContentKind.TEXT, text=line)
            await interaction.send_message(task.principal, payload)
        except Exception as e:
            _logger.send_error(f"停机交代发送失败: {task.principal.key}", e)

    dead = await purge_dead_tasks(conn)
    _logger.info(f"停机交代 {len(rows)} 串，判死 {dead} 条")
