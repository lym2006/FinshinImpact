# src/plugins/AI/services/_receipt.py
"""停机交代服务

- 重启时对欠答问答逐主体补说
- 说完才结算这批任务行
"""

import random
import re

from core.contracts import CapabilityCall
from core.domain import ChatRole
from core.domain.ids import ContainerKey
from core.dto import PrincipalDTO, TaskDTO
from data import build_repositories, get_connection, purge_dead_tasks
from utils import get_logger
from utils.paths import DB_FILE

from ..config import ai_config
from ..core import AIClient
from ..markdown import strip_model_marks
from ..utils import build_message

_logger = get_logger("Plg.AI.Receipt")

_CANDIDATE_COUNT = 5  # 一次现写要几句候选

# 配置没填话术时的现写指令，只说自己回来了，不讲刚才去做什么
_COMPOSE_PROMPT = (
    "你刚才不在，漏答了对方的话，现在补一句说自己回来了\n"
    f"给出 {_CANDIDATE_COUNT} 句不同的说法，每句一行，不要编号和项目符号\n"
    "要求：\n"
    "1. 每句只说自己回来了、来找对方说话或来陪对方了\n"
    "2. 不讲刚才去了哪里、做了什么，不提程序、断线与故障\n"
    "3. 不超过 30 字，不报漏了几句，不催对方再说一遍\n"
    "4. 句与句的用词不重复\n"
    "5. 纯文本，不加引号、标题与任何样式标记\n"
)

# 指令并到人设那条系统轮尾，用户轮只留一句让它开口
_COMPOSE_ASK = "把这几句直接说出来"

# 行首的编号与项目符号
_LIST_MARK_RE = re.compile(r"^\s*(?:[-*+]|\d+[.、)])\s*")

_QUOTE_CHARS = "\"'“”‘’「」『』"

# 指令限 30 字，留出标点余量，拒答与铺陈的长句在这道就被丢掉
_LINE_CHAR_LIMIT = 40


async def report_lost_tasks(call: CapabilityCall) -> None:
    """补说停机期间欠下的问答

    - 引擎开跑前逐会话各补一句，没欠账即一句不说
    - 配置填了话术即随机取一句，留空即交模型现写
    - 补的那句不进历史，欠答的消息本身也没入库
    - 说不出去的记一笔错误，欠下的账整批判死
    """
    conn = await get_connection(DB_FILE)
    rows = await build_repositories(conn).task.list_all_unfinished()
    if not rows:
        return

    targets = _one_per_container(rows)
    lines = ai_config.lost_lines
    used: set[str] = set()
    for principal in targets:
        try:
            text = random.choice(lines) if lines else await _compose_line(used)
            if not text:
                _logger.error(f"{principal.key} 交代现写为空，本条不补说")
                continue
            await call.say(principal, text)
        except Exception as e:
            _logger.send_error(f"停机交代失败: {principal.key}", e)

    dead = await purge_dead_tasks(conn)
    _logger.info(f"停机交代 {len(rows)} 串、{len(targets)} 个会话，判死 {dead} 条")


def _one_per_container(rows: tuple[TaskDTO, ...]) -> list[PrincipalDTO]:
    """同会话的多行欠账只留首个欠答者，按欠账出现的先后排"""
    targets: dict[ContainerKey, PrincipalDTO] = {}
    for row in rows:
        targets.setdefault(row.principal.container, row.principal)
    return list(targets.values())


async def _compose_line(used: set[str]) -> str:
    """现写候选里随机挑一句说，本次启动说过的那句不重取

    - 候选全说过时随机重取，这个会话不漏
    """
    candidates = await _compose_candidates()
    if not candidates:
        return ""
    fresh = [line for line in candidates if line not in used]
    text = random.choice(fresh or candidates)
    used.add(text)
    return text


async def _compose_candidates() -> list[str]:
    """交当前人设现写一轮，把几句候选拆开交出"""
    persona = ai_config.init[0]["content"]

    # 指令并进用户轮会被人设的抗注入条款当成外人使唤
    turns = [
        build_message(ChatRole.SYSTEM, f"{persona}\n\n{_COMPOSE_PROMPT}"),
        build_message(ChatRole.USER, _COMPOSE_ASK),
    ]

    current = ""
    async for delta in AIClient.stream_chat(turns):
        if (content := delta.get("content")) is not None:
            current += content

    return _split_candidates(strip_model_marks(current))


def _split_candidates(raw: str) -> list[str]:
    """把现写的候选按行拆开，去掉编号、项目符号与包裹的引号"""
    lines: list[str] = []
    for chunk in raw.splitlines():
        text = _LIST_MARK_RE.sub("", chunk).strip().strip(_QUOTE_CHARS).strip()
        if not text or len(text) > _LINE_CHAR_LIMIT:
            continue
        if text not in lines:
            lines.append(text)
    return lines
