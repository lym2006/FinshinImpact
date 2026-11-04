# devtools/tests/test_plugin_background.py
"""插件契约与时机订阅的单元测试

- stdlib unittest，打桩导入与注册序列，不触网
- 运行：python -m unittest tests.test_plugin_background -v
- 回归点 1：注册表把插件声明的常驻协程与时机订阅随报告一起交出
- 回归点 2：路由缺失或声明形态不对的插件不交出协程
- 回归点 3：非 callable 成员丢弃
- 回归点 4：轮询退出即拉起并取消常驻协程
- 回归点 5：协程抛错只记录，不穿透引擎线程
- 回归点 6：AI 插件把清理协程、问答任务处理与时机订阅交进契约
- 回归点 7：注册表只认路由清单，清单交给注入的编译器组装
- 回归点 8：插件声明的任务处理随报告一起交出
- 回归点 9：时机订阅按时机归组交出，形态非法整条丢
- 回归点 10：引擎开跑前逐个跑订阅了它的件，交出的只有说话那一路，报错不挡轮询
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
from bot._service import AdapterRuntime  # noqa: E402
from core.contracts import CapabilityCall  # noqa: E402
from core.domain import (  # noqa: E402
    PLUGINS_PKG,
    Platform,
    PlatformTiming,
    PluginRoute,
    PluginSpec,
    PluginTiming,
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

    - 返回 (报告, 协程, 任务处理, 时机订阅) 与收到的路由
    """

    def fake_import(full: str) -> object:
        found = modules[full.rsplit(".", 1)[-1]]
        if isinstance(found, Exception):
            raise found
        return found

    dispatcher = _FakeDispatcher()
    manifests = [SimpleNamespace(name=name, help_section=()) for name in names]

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


async def _say(principal: object, text: str) -> None:
    """占位的外发出口，测试里说话不碰真端口"""
    await asyncio.sleep(0)


_CAPABILITY = CapabilityCall(say=_say)  # 召唤插件时交出去的那份交代


class TestCollectBackgrounds(unittest.TestCase):
    """回归点 1/2/3/7"""

    def test_declared_hooks_returned_with_report(self) -> None:
        """声明了常驻协程与时机订阅的插件一并交出，并进成功报告"""
        modules = {
            "AI": _plugin(
                backgrounds=(_noop,),
                timings=(PluginTiming(PlatformTiming.IDENTITY_CHANGED, _noop),),
            )
        }

        (report, hooks, _, timings), routers = _register_modules(modules, ["AI"])

        self.assertEqual(hooks, (_noop,))
        self.assertEqual(timings, {PlatformTiming.IDENTITY_CHANGED: (_noop,)})
        self.assertEqual(report, [("AI", None)])
        self.assertEqual(len(routers), 1)
        self.assertEqual(len(routers[0].compiled.routes), 1)

    def test_spec_missing_skips_hooks(self) -> None:
        """缺清单的插件记失败且不交出协程"""
        modules = {"AI": SimpleNamespace(backgrounds=(_noop,)), "help": _plugin()}

        (report, hooks, _, timings), routers = _register_modules(
            modules, ["AI", "help"]
        )

        self.assertEqual(hooks, ())
        self.assertEqual(timings, {}, "缺清单的插件不该交出时机订阅")
        self.assertEqual(len(routers), 1)
        self.assertIsInstance(report[0][1], PluginSpecError)
        self.assertIsNone(report[1][1])

    def test_legacy_router_not_mounted(self) -> None:
        """只交 router 的插件记加载失败"""
        modules = {"bad": SimpleNamespace(router=object()), "good": _plugin()}

        (report, hooks, _, timings), routers = _register_modules(
            modules, ["bad", "good"]
        )

        self.assertIsInstance(report[0][1], PluginSpecError)
        self.assertIsNone(report[1][1])
        self.assertEqual(hooks, ())
        self.assertEqual(timings, {})
        self.assertEqual(len(routers), 1)

    def test_module_missing_kinds(self) -> None:
        """插件本身缺席与内部缺依赖记成两种异常"""
        modules = {
            "gone": ModuleNotFoundError(f"No module named '{PLUGINS_PKG}.gone'"),
            "deps": ModuleNotFoundError("No module named 'numpy'"),
            "good": _plugin(),
        }

        (report, _, _, _), _ = _register_modules(modules, ["gone", "deps", "good"])

        self.assertIsInstance(report[0][1], PluginMissingError)
        self.assertIsInstance(report[1][1], PluginDependencyError)
        self.assertIsNone(report[2][1])

    def test_non_callable_member_dropped(self) -> None:
        """声明里混进非 callable 只丢该成员"""
        modules = {"AI": _plugin(backgrounds=(_noop, "拼错了"))}

        (_, hooks, _, timings), _ = _register_modules(modules, ["AI"])

        self.assertEqual(hooks, (_noop,))
        self.assertEqual(timings, {})

    def test_bad_shape_reported_and_excluded(self) -> None:
        """backgrounds 不是列表或元组即记失败，协程不收"""
        modules = {
            "bad": _plugin(backgrounds=_noop),
            "good": _plugin(backgrounds=(_noop,)),
        }

        (report, hooks, _, timings), routers = _register_modules(
            modules, ["bad", "good"]
        )

        self.assertEqual(hooks, (_noop,))
        self.assertEqual(timings, {})
        self.assertEqual(len(routers), 1)
        self.assertEqual([row[0] for row in report], ["bad", "good"])
        self.assertIsInstance(report[0][1], PluginLoadError)
        self.assertIsNone(report[1][1])

    def test_undeclared_plugin_yields_empty(self) -> None:
        """未声明常驻协程的插件照常注册，协程为空"""
        modules = {"help": _plugin()}

        (report, hooks, handlers, timings), _ = _register_modules(modules, ["help"])

        self.assertEqual(hooks, ())
        self.assertEqual(timings, {})
        self.assertEqual(handlers, ())
        self.assertEqual(report, [("help", None)])

    def test_declared_task_handlers_returned(self) -> None:
        """回归点 8：声明了任务处理的插件交出处理清单"""
        declared = TaskHandler(kind=TaskKind.CHAT, run=_handle)
        modules = {"AI": _plugin(task_handlers=(declared,)), "help": _plugin()}

        (_, _, handlers, _), _ = _register_modules(modules, ["AI", "help"])

        self.assertEqual(handlers, (declared,))

    def test_timings_grouped_by_platform_moment(self) -> None:
        """回归点 9：时机订阅按时机归组交出，同组按交出的先后排

        - 形态非法的整条插件记失败，一条订阅不收
        """
        second = _plugin(
            timings=(
                PluginTiming(PlatformTiming.BEFORE_ENGINE_RUN, _handle),
                PluginTiming(PlatformTiming.BEFORE_ENGINE_RUN, _noop),
            )
        )
        modules = {
            "bad": _plugin(timings=_noop),
            "AI": _plugin(
                timings=(PluginTiming(PlatformTiming.IDENTITY_CHANGED, _noop),)
            ),
            "other": second,
        }

        (report, _, _, timings), _ = _register_modules(modules, ["AI", "other", "bad"])

        self.assertEqual(timings[PlatformTiming.IDENTITY_CHANGED], (_noop,))
        self.assertEqual(timings[PlatformTiming.BEFORE_ENGINE_RUN], (_handle, _noop))
        self.assertIsInstance(report[2][1], PluginLoadError)

    def test_non_plugin_timing_entry_rejected(self) -> None:
        """timings 里混进非订阅条目即整条插件记失败"""
        modules = {"alpha": _plugin(timings=(_noop,)), "beta": _plugin()}

        (report, _, _, timings), _ = _register_modules(modules, ["alpha", "beta"])

        self.assertEqual(timings, {})
        self.assertIsInstance(report[0][1], PluginLoadError)
        self.assertIsNone(report[1][1])


class _FakeAdapter:
    """只喂 _polling_task 需要的 start 协程、释放连接与外发端口"""

    def __init__(self) -> None:
        self.closed = 0
        self.interaction = SimpleNamespace(name="外发端口")
        self.platform = Platform.TELEGRAM

    async def start(self) -> None:
        """让出一轮调度后结束本轮轮询"""
        await asyncio.sleep(0)

    async def close(self) -> None:
        """释放连接，记一笔次数"""
        self.closed += 1

    def is_link_failure(self, exc: BaseException) -> bool:
        """假适配器不判链路，异常一律不退避"""
        return False


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

        service = AdapterRuntime(_FakeAdapter(), _CAPABILITY, (hook,))  # type: ignore[arg-type]
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

        service = AdapterRuntime(_FakeAdapter(), _CAPABILITY, (boom,))  # type: ignore[arg-type]
        with patch.object(service_module._logger, "send_error", new=_send_error):
            await service._polling_task()

        self.assertEqual(len(sent), 1, "协程异常应记录一次")
        self.assertIsInstance(sent[0][1], ValueError)

    async def test_no_hooks_still_releases_connection(self) -> None:
        """未声明协程时收尾路径照常释放连接"""
        adapter = _FakeAdapter()
        service = AdapterRuntime(adapter, _CAPABILITY)  # type: ignore[arg-type]
        await service._polling_task()

        self.assertEqual(adapter.closed, 1)


class TestServiceRunsBeforeRun(unittest.IsolatedAsyncioTestCase):
    """回归点 10"""

    async def test_before_run_hooks_run_before_polling(self) -> None:
        """引擎开跑前逐个跑订阅了它的件，交出的只有那份交代"""
        seen: list[object] = []

        class _OrderedAdapter(_FakeAdapter):
            async def start(self) -> None:
                seen.append("轮询开跑")

        async def before_run(call: CapabilityCall) -> None:
            seen.append(call)

        adapter = _OrderedAdapter()
        service = AdapterRuntime(adapter, _CAPABILITY, (), (before_run,))  # type: ignore[arg-type]
        await service._polling_task()

        self.assertEqual(seen, [_CAPABILITY, "轮询开跑"])

    async def test_before_run_crash_is_logged_and_polling_runs(self) -> None:
        """订阅了引擎开跑前的件抛错只落日志，轮询照常开跑、收尾照常释放连接"""
        sent: list[tuple[str, BaseException]] = []

        def _send_error(desc: str, exc: BaseException) -> None:
            sent.append((desc, exc))

        async def boom(call: CapabilityCall) -> None:
            raise ValueError("交代失败")

        adapter = _FakeAdapter()
        service = AdapterRuntime(adapter, _CAPABILITY, (), (boom,))  # type: ignore[arg-type]
        with patch.object(service_module._logger, "send_error", new=_send_error):
            await service._polling_task()

        self.assertEqual(len(sent), 1, "引擎开跑前的件异常应记录一次")
        self.assertIsInstance(sent[0][1], ValueError)
        self.assertEqual(adapter.closed, 1)


class TestAIPluginDeclares(unittest.TestCase):
    """回归点 6"""

    def test_cleanup_loop_is_declared(self) -> None:
        """AI 插件把过期清理协程、问答任务处理与三个平台机会的订阅交进契约"""
        from bundled.AI import spec
        from bundled.AI.core import purge_on_identity_changed
        from bundled.AI.services import (
            chat_task_handler,
            cleanup_loop,
            report_lost_tasks,
            wake_cleanup,
        )

        self.assertEqual(spec.backgrounds, (cleanup_loop,))
        self.assertEqual(spec.task_handlers, (chat_task_handler,))
        self.assertEqual(
            spec.timings,
            (
                PluginTiming(PlatformTiming.BEFORE_ENGINE_RUN, report_lost_tasks),
                PluginTiming(
                    PlatformTiming.IDENTITY_CHANGED, purge_on_identity_changed
                ),
                PluginTiming(PlatformTiming.CONFIG_VERIFIED, wake_cleanup),
            ),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
