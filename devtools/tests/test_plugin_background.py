# devtools/tests/test_plugin_background.py
"""插件常驻协程契约的单元测试

- stdlib unittest，打桩导入与注册序列，不触网
- 运行：python -m unittest tests.test_plugin_background -v
- 回归点 1：注册表把插件声明的协程与历史清理入口随报告一起交出
- 回归点 2：路由缺失或声明形态不对的插件不交出协程
- 回归点 3：非 callable 成员丢弃
- 回归点 4：轮询退出即拉起并取消常驻协程
- 回归点 5：协程抛错只记录，不穿透引擎线程
- 回归点 6：AI 插件把清理协程、会话清理入口与问答任务处理交进契约
- 回归点 7：注册表只认路由清单，清单交给注入的编译器组装
- 回归点 8：插件声明的任务处理随报告一起交出
- 回归点 9：插件声明的启动交代随报告一起交出，形态非法整条丢
- 回归点 10：引擎开跑前逐个调启动交代并只交外发端口，报错不挡轮询
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
from core.domain import (  # noqa: E402
    PLUGINS_PKG,
    PluginRoute,
    PluginSpec,
    TaskHandler,
    TaskKind,
)
from exceptions import (  # noqa: E402
    PluginDependencyError,
    PluginLoadError,
    PluginMissingError,
    PluginSpecError,
)
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

    - 返回 (报告, 协程, 清理入口, 任务处理, 启动交代) 与收到的路由
    """

    def fake_import(full: str) -> object:
        found = modules[full.rsplit(".", 1)[-1]]
        if isinstance(found, Exception):
            raise found
        return found

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


def _plugin(**spec_fields: object) -> SimpleNamespace:
    """拼一只只交路由清单的假插件模块"""
    routes = (PluginRoute(_never, _handle),)
    return SimpleNamespace(spec=PluginSpec(routes=routes, **spec_fields))


class TestCollectBackgrounds(unittest.TestCase):
    """回归点 1/2/3/7"""

    def test_declared_hooks_returned_with_report(self) -> None:
        """声明了常驻协程的插件交出协程并进成功报告"""
        modules = {"AI": _plugin(backgrounds=(_noop,), history_reset=_noop)}

        (report, hooks, resets, _, _), routers = _register_modules(modules, ["AI"])

        self.assertEqual(hooks, (_noop,))
        self.assertEqual(resets, (_noop,))
        self.assertEqual(report, [("AI", None)])
        self.assertEqual(len(routers), 1)
        self.assertEqual(len(routers[0].compiled.routes), 1)

    def test_spec_missing_skips_hooks(self) -> None:
        """缺清单的插件记失败且不交出协程"""
        modules = {"AI": SimpleNamespace(backgrounds=(_noop,)), "help": _plugin()}

        (report, hooks, resets, _, _), routers = _register_modules(
            modules, ["AI", "help"]
        )

        self.assertEqual(hooks, ())
        self.assertEqual(resets, (), "缺清单的插件不该交出清理入口")
        self.assertEqual(len(routers), 1)
        self.assertIsInstance(report[0][1], PluginSpecError)
        self.assertIsNone(report[1][1])

    def test_legacy_router_not_mounted(self) -> None:
        """只交 router 的插件记加载失败"""
        modules = {"bad": SimpleNamespace(router=object()), "good": _plugin()}

        (report, hooks, resets, _, _), routers = _register_modules(
            modules, ["bad", "good"]
        )

        self.assertIsInstance(report[0][1], PluginSpecError)
        self.assertIsNone(report[1][1])
        self.assertEqual(hooks, ())
        self.assertEqual(resets, ())
        self.assertEqual(len(routers), 1)

    def test_module_missing_kinds(self) -> None:
        """插件本身缺席与内部缺依赖记成两种异常"""
        modules = {
            "gone": ModuleNotFoundError(f"No module named '{PLUGINS_PKG}.gone'"),
            "deps": ModuleNotFoundError("No module named 'numpy'"),
            "good": _plugin(),
        }

        (report, _, _, _, _), _ = _register_modules(modules, ["gone", "deps", "good"])

        self.assertIsInstance(report[0][1], PluginMissingError)
        self.assertIsInstance(report[1][1], PluginDependencyError)
        self.assertIsNone(report[2][1])

    def test_non_callable_member_dropped(self) -> None:
        """声明里混进非 callable 只丢该成员"""
        modules = {"AI": _plugin(backgrounds=(_noop, "拼错了"))}

        (_, hooks, resets, _, _), _ = _register_modules(modules, ["AI"])

        self.assertEqual(hooks, (_noop,))
        self.assertEqual(resets, ())

    def test_bad_shape_reported_and_excluded(self) -> None:
        """backgrounds 不是列表或元组即记失败，协程不收"""
        modules = {
            "bad": _plugin(backgrounds=_noop),
            "good": _plugin(backgrounds=(_noop,)),
        }

        (report, hooks, resets, _, _), routers = _register_modules(
            modules, ["bad", "good"]
        )

        self.assertEqual(hooks, (_noop,))
        self.assertEqual(resets, ())
        self.assertEqual(len(routers), 1)
        self.assertEqual([row[0] for row in report], ["bad", "good"])
        self.assertIsInstance(report[0][1], PluginLoadError)
        self.assertIsNone(report[1][1])

    def test_undeclared_plugin_yields_empty(self) -> None:
        """未声明常驻协程的插件照常注册，协程为空"""
        modules = {"help": _plugin()}

        (report, hooks, resets, handlers, _), _ = _register_modules(modules, ["help"])

        self.assertEqual(hooks, ())
        self.assertEqual(resets, ())
        self.assertEqual(handlers, ())
        self.assertEqual(report, [("help", None)])

    def test_declared_task_handlers_returned(self) -> None:
        """回归点 8：声明了任务处理的插件交出处理清单"""
        declared = TaskHandler(kind=TaskKind.CHAT, run=_handle)
        modules = {"AI": _plugin(task_handlers=(declared,)), "help": _plugin()}

        (_, _, _, handlers, _), _ = _register_modules(modules, ["AI", "help"])

        self.assertEqual(handlers, (declared,))

    def test_declared_startups_returned(self) -> None:
        """回归点 9：声明了启动交代的插件交出入口，形态非法整条丢"""
        modules = {
            "bad": _plugin(startups=_noop),
            "AI": _plugin(startups=(_noop, "拼错了")),
        }

        (report, _, _, _, startups), _ = _register_modules(modules, ["bad", "AI"])

        self.assertEqual(startups, (_noop,))
        self.assertIsInstance(report[0][1], PluginLoadError)
        self.assertIsNone(report[1][1])


class _FakeSession:
    def __init__(self) -> None:
        self.closed = 0

    async def close(self) -> None:
        self.closed += 1


class _FakeAdapter:
    """只喂 _polling_task 需要的 start 协程、session 与外发端口"""

    def __init__(self) -> None:
        self.bot = SimpleNamespace(session=_FakeSession())
        self.interaction = SimpleNamespace(name="外发端口")

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


class TestServiceRunsStartups(unittest.IsolatedAsyncioTestCase):
    """回归点 10"""

    async def test_startups_run_before_polling(self) -> None:
        """启动交代先于轮询开跑，收到的只有外发端口"""
        seen: list[object] = []

        class _OrderedAdapter(_FakeAdapter):
            async def start(self) -> None:
                seen.append("轮询开跑")

        async def startup(interaction: object) -> None:
            seen.append(interaction)

        adapter = _OrderedAdapter()
        service = BotService(adapter, (), (startup,))  # type: ignore[arg-type]
        await service._polling_task()

        self.assertEqual(seen, [adapter.interaction, "轮询开跑"])

    async def test_startup_crash_is_logged_and_polling_runs(self) -> None:
        """交代入口抛错只落日志，轮询照常开跑、收尾照常关会话"""
        sent: list[tuple[str, BaseException]] = []

        def _send_error(desc: str, exc: BaseException) -> None:
            sent.append((desc, exc))

        async def boom(interaction: object) -> None:
            raise ValueError("交代失败")

        adapter = _FakeAdapter()
        service = BotService(adapter, (), (boom,))  # type: ignore[arg-type]
        with patch.object(service_module._logger, "send_error", new=_send_error):
            await service._polling_task()

        self.assertEqual(len(sent), 1, "交代入口异常应记录一次")
        self.assertIsInstance(sent[0][1], ValueError)
        self.assertEqual(adapter.bot.session.closed, 1)


class TestAIPluginDeclares(unittest.TestCase):
    """回归点 6"""

    def test_cleanup_loop_is_declared(self) -> None:
        """AI 插件把过期清理协程、会话清理入口、问答任务处理与停机交代交进契约"""
        from plugins.AI import spec
        from plugins.AI.core import purge_history
        from plugins.AI.services import (
            chat_task_handler,
            cleanup_loop,
            report_lost_tasks,
        )

        self.assertEqual(spec.backgrounds, (cleanup_loop,))
        self.assertIs(spec.history_reset, purge_history)
        self.assertEqual(spec.task_handlers, (chat_task_handler,))
        self.assertEqual(spec.startups, (report_lost_tasks,))


if __name__ == "__main__":
    unittest.main(verbosity=2)
