# src/bundled/AI/handlers/_history.py
"""历史命令

- /history：发送本容器的对话记录文档
- /clear：清除本容器的会话记忆与记录
"""

from pathlib import Path

from finshin_sdk import HandlerContext
from finshin_sdk.domain import CommandRole, ContentKind, PluginRoute
from finshin_sdk.domain.ids import SessionKey
from finshin_sdk.dto import OutboundPayloadDTO

from ..._shared.access import require_role
from ..._shared.filters import CommandMatch
from ..._shared.messages import BotMessage
from ..config import ai_config
from ..core import clear_session, purge_stale
from ..utils import make_session_key


def _get_file_path(key: SessionKey) -> Path:
    return ai_config.record_dir / f"{key}.md"


@require_role(CommandRole.ADMIN)
async def _show_history(platform_raw: object, ctx: HandlerContext) -> None:
    """发送历史记录

    - 人设或主人换过即先清干净，旧记录不会越过这次变更发出去
    """
    key = make_session_key(ctx.event.principal)
    await purge_stale(ai_config.init[0]["content"], key)
    file_path = _get_file_path(key)

    if not file_path.exists():
        await ctx.respond(BotMessage.HISTORY_EMPTY)
        return

    await ctx.respond(
        OutboundPayloadDTO(
            kind=ContentKind.DOCUMENT,
            text=BotMessage.HISTORY_CAPTION,
            local_path=str(file_path),
            file_name=file_path.name,
        )
    )


@require_role(CommandRole.ADMIN)
async def _clear_history(platform_raw: object, ctx: HandlerContext) -> None:
    """清除记忆"""
    key = make_session_key(ctx.event.principal)
    await clear_session(key)
    _get_file_path(key).unlink(missing_ok=True)
    await ctx.respond(BotMessage.HISTORY_MEMORY_CLEARED)


routes = (
    PluginRoute(CommandMatch("history"), _show_history),
    PluginRoute(CommandMatch("clear"), _clear_history),
)
