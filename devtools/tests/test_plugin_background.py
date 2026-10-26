# devtools/tests/test_plugin_background.py
"""插件常驻协程契约的单元测试

- stdlib unittest，打桩导入与注册序列，不触网
- 运行：python -m unittest tests.test_plugin_background -v
- 回归点 1：注册表把插件声明的协程随报告一起交出
- 回归点 2：路由缺失或声明形态不对的插件不交出协程
- 回归点 3：非 callable 成员丢弃
- 回归点 4：轮询退出即拉起并取消常驻协程
- 回归点 5：协程抛错只记录，不穿透引擎线程
- 回归点 6：AI 插件把清理协程交进契约
- 回归点 7：注册表新旧两套契约并认，spec 走注入的编译器
"""

import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from bot import _service as service_module  # noqa: E402
from bot._service import BotService  # noqa: E402
from core.domain import PluginRoute, PluginSpec  # noqa: E402
from utils.plugin import _register  # noqa: E402


async def _noop() -> None:
    """占位常驻协程"""
    await asyncio.sleep(0)


async def _never(ctx: object) -> bool:
    """占位谓词，什么都不接管"""
    return False


async def _handle(raw: object, ctx: object) -> None:
    """占位处理函数"""
    await asyncio.sleep(0)


class _FakeDispatcher:
    def __init__(self) -> None:
        self.routers: list[object] = []

    def include_router(self, router: object) -> None:
        self.routers.append(router)


def _register_modules(modules: dict[str, object], names: list[str]):
    """按假插件表跑一轮注册

    - 返回 (报告, 协程) 与收到的路由
    """

    def fake_import(full: str) -> object:
        return modules[full.rsplit(".", 1)[-1]]

    dispatcher = _FakeDispatcher()
    manifests = [SimpleNamespace(name=name, core=False) for name in names]

    with (
        patch.object(_register, "_resolve_plugins", lambda: manifests),
        patch.object(_register.importlib, "import_module", fake_import),
    ):
        result = _register.register_plugins(dispatcher, _compile)  # type: ignore[arg-type]

    return result, dispatcher.routers


def _compile(spec: object) -> SimpleNamespace:
    """假编译器：把清单原样裹进一只待挂对象"""
    return SimpleNamespace(compiled=spec)


def _plugin(**attrs: object) -> SimpleNamespace:
    """拼一个假插件模块"""
    return SimpleNamespace(router=SimpleNamespace(), **attrs)


class TestCollectBackgrounds(unittest.TestCase):
    """回归点 1/2/3"""

    def test_declared_hooks_returned_with_report(self) -> None:
        """声明了 backgrounds 的插件交出协程并进成功报告"""
        modules = {"AI": _plugin(backgrounds=(_noop,))}

        (report, hooks), routers = _register_modules(modules, ["AI"])

        self.assertEqual(hooks, (_noop,))
        self.assertEqual(report, [("AI", True, "")])
        self.assertEqual(len(routers), 1)

    def test_router_missing_skips_hooks(self) -> None:
        """缺 router 的插件记失败且不交出协程"""
        modules = {"AI": SimpleNamespace(backgrounds=(_noop,)), "help": _plugin()}

        (report, hooks), routers = _register_modules(modules, ["AI", "help"])

        self.assertEqual(hooks, ())
        self.assertEqual(len(routers), 1)
        self.assertFalse(report[0][1])
        self.assertTrue(report[1][1])

    def test_non_callable_member_dropped(self) -> None:
        """声明里混进非 callable 只丢该成员"""
        modules = {"AI": _plugin(backgrounds=(_noop, "拼错了"))}

        (_, hooks), _ = _register_modules(modules, ["AI"])

        self.assertEqual(hooks, (_noop,))

    def test_bad_shape_reported_and_excluded(self) -> None:
        """backgrounds 不是列表或元组即记失败，协程不收"""
        modules = {
            "bad": _plugin(backgrounds=_noop),
            "good": _plugin(backgrounds=(_noop,)),
        }

        (report, hooks), routers = _register_modules(modules, ["bad", "good"])

        self.assertEqual(hooks, (_noop,))
        self.assertEqual(len(routers), 1)
        self.assertEqual([row[0] for row in report], ["bad", "good"])
        self.assertFalse(report[0][1])
        self.assertTrue(report[1][1])

    def test_undeclared_plugin_yields_empty(self) -> None:
        """未声明 backgrounds 的插件照常注册，协程为空"""
        modules = {"help": _plugin()}

        (report, hooks), _ = _register_modules(modules, ["help"])

        self.assertEqual(hooks, ())
        self.assertEqual(report, [("help", True, "")])


class TestSpecContract(unittest.TestCase):
    """回归点 7：新旧两套契约并认"""

    def test_spec_compiled_and_hooks_from_spec(self) -> None:
        """只交 spec 的插件走注入的编译器，协程取自清单"""
        spec = PluginSpec(routes=(PluginRoute(_never, _handle),), backgrounds=(_noop,))
        modules = {"AI": SimpleNamespace(spec=spec)}

        (report, hooks), routers = _register_modules(modules, ["AI"])

        self.assertEqual(report, [("AI", True, "")])
        self.assertEqual(hooks, (_noop,))
        self.assertEqual(routers[0].compiled, spec)

    def test_spec_wins_over_legacy_router(self) -> None:
        """两套都交时按新契约走，旧 Router 不进注册表"""
        spec = PluginSpec()
        modules = {"AI": SimpleNamespace(spec=spec, router=object())}

        (_, _), routers = _register_modules(modules, ["AI"])

        self.assertEqual(routers[0].compiled, spec)

    def test_missing_both_reports_reason(self) -> None:
        """router 与 spec 都没有才记失败，原因点名两套契约"""
        modules = {"bad": SimpleNamespace(), "good": _plugin()}

        (report, hooks), routers = _register_modules(modules, ["bad", "good"])

        self.assertFalse(report[0][1])
        self.assertIn("缺少 router 或 spec", report[0][2])
        self.assertTrue(report[1][1])
        self.assertEqual(hooks, ())
        self.assertEqual(len(routers), 1)

    def test_spec_backgrounds_shape_checked(self) -> None:
        """清单里的 backgrounds 形态不对同样记失败"""
        modules = {
            "bad": SimpleNamespace(spec=PluginSpec(backgrounds=_noop)),
            "good": SimpleNamespace(spec=PluginSpec(backgrounds=(_noop,))),
        }

        (report, hooks), routers = _register_modules(modules, ["bad", "good"])

        self.assertFalse(report[0][1])
        self.assertTrue(report[1][1])
        self.assertEqual(hooks, (_noop,))
        self.assertEqual(len(routers), 1)


class _FakeSession:
    def __init__(self) -> None:
        self.closed = 0

    async def close(self) -> None:
        self.closed += 1


class _FakeAdapter:
    """只喂 _polling_task 需要的 start 协程与 session"""

    def __init__(self) -> None:
        self.bot = SimpleNamespace(session=_FakeSession())

    async def start(self) -> None:
        """让出一轮调度后结束本轮轮询"""
        await asyncio.sleep(0)


class TestServiceRunsHooks(unittest.IsolatedAsyncioTestCase):
    """回归点 4/5"""

    async def test_hooks_start_and_cancel_with_polling(self) -> None:
        """轮询收尾即取消常驻协程，协程自己收到取消"""
        seen = {"ran": 0, "cancelled": False}

        async def hook() -> None:
            seen["ran"] += 1
            try:
                await asyncio.sleep(3600)
            except asyncio.CancelledError:
                seen["cancelled"] = True
                raise

        service = BotService(_FakeAdapter(), (hook,))  # type: ignore[arg-type]
        await service._polling_task()

        self.assertEqual(seen["ran"], 1, "常驻协程未随轮询启动")
        self.assertTrue(seen["cancelled"], "轮询退出未取消常驻协程")

    async def test_hook_crash_is_logged_not_raised(self) -> None:
        """协程抛错只落日志，不穿透到线程兜底"""
        sent: list[tuple[str, BaseException]] = []

        def _send_error(desc: str, exc: BaseException) -> None:
            sent.append((desc, exc))

        async def boom() -> None:
            raise ValueError("boom")

        service = BotService(_FakeAdapter(), (boom,))  # type: ignore[arg-type]
        with patch.object(service_module._logger, "send_error", new=_send_error):
            await service._polling_task()

        self.assertEqual(len(sent), 1, "协程异常应记录一次")
        self.assertIsInstance(sent[0][1], ValueError)

    async def test_no_hooks_still_closes_session(self) -> None:
        """未声明协程时收尾路径一字不动"""
        adapter = _FakeAdapter()
        service = BotService(adapter)  # type: ignore[arg-type]
        await service._polling_task()

        self.assertEqual(adapter.bot.session.closed, 1)


class TestAIPluginDeclares(unittest.TestCase):
    """回归点 6"""

    def test_cleanup_loop_is_declared(self) -> None:
        """AI 插件把过期清理协程交进契约"""
        from plugins.AI import spec
        from plugins.AI.services import cleanup_loop

        self.assertEqual(spec.backgrounds, (cleanup_loop,))


if __name__ == "__main__":
    unittest.main(verbosity=2)
