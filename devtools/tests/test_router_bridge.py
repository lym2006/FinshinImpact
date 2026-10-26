# devtools/tests/test_router_bridge.py
"""插件清单编译的单元测试

- stdlib unittest，走真 Dispatcher 喂归一中间件，不触网
- 运行：python -m pytest devtools/tests/test_router_bridge.py -v
- 回归点 1：同份清单每次编译交出全新一只 Router
- 回归点 2：routes 的顺序即匹配优先级，先判真的那条办完即停
- 回归点 3：谓词只吃归一后的处理上下文，处理函数按位置收原始消息
- 回归点 4：一条都不判真时不进任何处理函数
"""

import asyncio
import sys
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from aiogram import Dispatcher  # noqa: E402
from aiogram.types import Chat, Message, Update, User  # noqa: E402

from adapters.telegram._normalize import NormalizeMiddleware  # noqa: E402
from adapters.telegram.router_bridge import _Predicate, build_router  # noqa: E402
from core.domain import PluginRoute, PluginSpec  # noqa: E402
from services.context import HandlerContext  # noqa: E402

_GROUP = Chat(id=-100123, type="supergroup", title="测试群")
_USER = User(id=456, is_bot=False, first_name="三")
_BOT = User(id=777, is_bot=True, first_name="机器人", username="MyBot")


class _FakeBot:
    """只回答自身身份的假 bot"""

    id = 777

    async def me(self) -> User:
        return _BOT


class _SilentInteraction:
    """不外发内容的假交互端口"""

    async def send_message(self, principal: Any, payload: Any, **_kw: Any) -> None:
        return None

    def mention_fragment(self, principal: Any) -> str:
        return ""


def _route(sink: list[str], name: str, head: str) -> PluginRoute:
    """拼一条只认指定命令名的路由

    - 处理函数记下原始消息与上下文的类型，形参注入走样即留下不同读数
    """

    async def predicate(ctx: HandlerContext) -> bool:
        return ctx.event.command.head == head

    async def handler(raw: Message, ctx: HandlerContext) -> None:
        sink.append(f"{name}:{type(raw).__name__}:{type(ctx).__name__}")

    return PluginRoute(predicate, handler)


def _spec(*heads: str, sink: list[str]) -> PluginSpec:
    """按命令名序列拼一份清单，路由名取自所在位次"""
    return PluginSpec(
        routes=tuple(
            _route(sink, f"r{index}", head) for index, head in enumerate(heads, 1)
        )
    )


class TestContractShape(unittest.TestCase):
    """回归点 1/4 的外壳"""

    def test_new_router_per_call(self) -> None:
        """同份清单两次编译交出两只不同的 Router"""
        spec = PluginSpec(routes=())

        self.assertIsNot(build_router(spec), build_router(spec))

    def test_no_context_never_taken(self) -> None:
        """拿不到处理上下文即不接管"""

        async def predicate(ctx: HandlerContext) -> bool:
            return True

        self.assertFalse(asyncio.run(_Predicate(predicate)(raw=None)))


def _make_message(text: str) -> Message:
    """构造一条群消息"""
    return Message(
        message_id=7,
        date=datetime(2026, 10, 26, 12, 0),
        chat=_GROUP,
        from_user=_USER,
        content_type="text",
        text=text,
    )


class _DispatchCase(unittest.IsolatedAsyncioTestCase):
    """把编译出的路由挂上真 Dispatcher 跑一条消息"""

    def setUp(self) -> None:
        self.sink: list[str] = []
        self.dispatcher = Dispatcher()
        self.dispatcher.update.outer_middleware(
            NormalizeMiddleware(_SilentInteraction(), bot=_FakeBot())  # type: ignore[arg-type]
        )

    async def _feed(self, text: str) -> None:
        """喂一条群消息"""
        await self.dispatcher.feed_update(
            _FakeBot(),  # type: ignore[arg-type]
            Update(update_id=1, message=_make_message(text)),
        )


class TestCompiledRoutes(_DispatchCase):
    """回归点 2/3/4"""

    async def test_first_matching_route_wins(self) -> None:
        """两条都判真时只有先声明的那条办成"""
        self.dispatcher.include_router(
            build_router(_spec("ping", "ping", sink=self.sink))
        )

        await self._feed("/ping")

        self.assertEqual(self.sink, ["r1:Message:HandlerContext"])

    async def test_later_route_takes_what_earner_refused(self) -> None:
        """前面的判假即让给后面的"""
        self.dispatcher.include_router(
            build_router(_spec("pong", "ping", sink=self.sink))
        )

        await self._feed("/ping")

        self.assertEqual(self.sink, ["r2:Message:HandlerContext"])

    async def test_no_route_matches_stays_silent(self) -> None:
        """一条都不判真时不进任何处理函数"""
        self.dispatcher.include_router(build_router(_spec("ping", sink=self.sink)))

        await self._feed("/nope")

        self.assertEqual(self.sink, [])

    async def test_empty_spec_is_harmless(self) -> None:
        """空清单挂上去不影响事件流"""
        self.dispatcher.include_router(build_router(PluginSpec()))

        await self._feed("/ping")

        self.assertEqual(self.sink, [])


if __name__ == "__main__":
    unittest.main()
