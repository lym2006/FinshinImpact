# src/plugins/AI/handlers/_history.py
"""历史命令

- /history：发送本容器的对话记录文档
- /clear：清除本容器的会话记忆与记录
"""

from pathlib import Path

from aiogram.types import Message

from core.domain import CommandRole, ContentKind, PluginRoute
from core.domain.ids import SessionKey
from core.dto import OutboundPayloadDTO
from services.context import HandlerContext

from ..._shared.access import require_role
from ..._shared.filters import CommandMatch
from ..._shared.messages import BotMessage
from ..config import ai_config
from ..core import clear_session, session_guard
from ..utils import make_session_key


def _get_file_path(key: SessionKey) -> Path:
    return ai_config.record_dir / f"{key}.md"


@require_role(CommandRole.ADMIN)
@session_guard
async def _show_history(raw: Message, ctx: HandlerContext) -> None:
    """发送历史记录"""
    file_path = _get_file_path(make_session_key(ctx.event.principal))

    if not file_path.exists():
        await ctx.answer(BotMessage.HISTORY_EMPTY)
        return

    await ctx.answer(
        OutboundPayloadDTO(
            kind=ContentKind.DOCUMENT,
            text=BotMessage.HISTORY_CAPTION,
            local_path=str(file_path),
            file_name=file_path.name,
        )
    )


@require_role(CommandRole.ADMIN)
@session_guard
async def _clear_history(raw: Message, ctx: HandlerContext) -> None:
    """清除记忆"""
    key = make_session_key(ctx.event.principal)
    await clear_session(key)
    _get_file_path(key).unlink(missing_ok=True)
    await ctx.answer(BotMessage.HISTORY_MEMORY_CLEARED)


routes = (
    PluginRoute(CommandMatch("history"), _show_history),
    PluginRoute(CommandMatch("clear"), _clear_history),
)
