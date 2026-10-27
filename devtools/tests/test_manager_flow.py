# devtools/tests/test_manager_flow.py
"""BotManager 配置应用与关闭流程单元测试

- stdlib unittest，打桩网络层与子管理器，不触网
- 运行：python -m unittest tests.test_manager_flow -v
- 回归点 1：校验失败弹向导，保存重验直至通过并启动服务
- 回归点 2：关闭后保存事件被忽略，不再弹窗
- 回归点 3：并发保存去重，同一时刻只有一个应用任务
- 回归点 4：未预期异常经 catch_all 路由致命信号，不杀进程
- 回归点 5：信号彼此隔离，杜绝历史串扰事故
- 回归点 6：stop_polling 协程必须被 await
- 回归点 7：token 报错一律走致命通知退出，不弹配置向导
- 回归点 8：起轮询撞链路故障退避重试，非链路异常仍外抛
- 回归点 9：人设正文或主人变更后立即清掉会话与落盘记录
"""

import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from aiogram.exceptions import TelegramNetworkError  # noqa: E402
from aiogram.methods import GetMe  # noqa: E402

from bot._managers import BotManager, _apply  # noqa: E402
from bot._service import BotService  # noqa: E402
from core.domain import FieldKey  # noqa: E402
from ui import gui_bridge  # noqa: E402


class ManagerFlowTestBase(unittest.IsolatedAsyncioTestCase):
    """公共夹具

    - 隔离标志、信号接收者、子管理器
    """

    async def asyncSetUp(self) -> None:  # noqa: D102
        self.loop = asyncio.get_running_loop()
        self.manager = BotManager(self.loop)

        # 向导信号捕获
        self.force_events: list[dict] = []
        self._sig_force = gui_bridge.request_force_setup

        def _capture(errors: dict | None = None) -> None:
            self.force_events.append(errors or {})

        self._capture = _capture
        self._sig_force.connect(_capture, f"test-force-{self.id()}")
        self.addCleanup(lambda: self._sig_force._instance.disconnect(_capture))

        # 隔离跨用例残留标志
        self._old_pending = gui_bridge._is_shutdown_pending
        gui_bridge._is_shutdown_pending = False
        self.addCleanup(setattr, gui_bridge, "_is_shutdown_pending", self._old_pending)
        gui_bridge.shutdown_completed_event.clear()

        # 实例级打桩子管理器（不绑定 self）
        sm = self.manager._settings_manager
        vm = self.manager._service_manager

        patches = [
            patch.object(type(self.manager._initializer), "execute", new=AsyncMock()),
            patch.object(sm, "execute", new=AsyncMock()),
            patch.object(vm, "stop_service"),
        ]

        # 可控验证桩：按队列返回，失败时同步填 last_errors
        self.verify_results: list[bool] = []
        self.verify_calls = 0
        self.service_starts = {"n": 0}

        async def _fake_verify() -> bool:
            self.verify_calls += 1
            ok = self.verify_results.pop(0) if self.verify_results else True
            if not ok:
                sm.last_errors = {FieldKey.PROXY: "代理不通"}
            return ok

        async def _count_start() -> None:
            self.service_starts["n"] += 1

        patches += [
            patch.object(sm, "verify_connectivity", new=_fake_verify),
            patch.object(vm, "execute", new=_count_start),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    async def _drain(self, times: int = 80) -> None:
        """给 loop 若干次调度机会"""
        for _ in range(times):
            await asyncio.sleep(0)


class TestApplyConfig(ManagerFlowTestBase):
    """回归点 1/3

    - 应用-弹窗-重验闭环
    """

    async def test_fail_then_save_then_pass_starts_service(self) -> None:
        """失败弹向导 → 保存重验 → 通过启动服务"""
        self.verify_results = [False, True]

        await self.manager._applier.apply_config()

        self.assertEqual(len(self.force_events), 1, "失败应弹出一次向导")
        self.assertIn(FieldKey.PROXY, self.force_events[0], "向导应携带字段错误")
        self.assertEqual(self.service_starts["n"], 0, "失败时不得启动服务")

        # 用户保存 → 重入校验
        self.manager.on_config_candidate()
        await self._drain()

        self.assertEqual(self.verify_calls, 2, "保存后必须重新校验")
        self.assertEqual(self.service_starts["n"], 1, "通过应启动服务")
        self.assertEqual(len(self.force_events), 1, "通过后不得再弹窗")

    async def test_concurrent_saves_deduplicated(self) -> None:
        """校验挂起期间连续保存

        - 只跑一个应用任务
        """
        gate = asyncio.Event()

        async def _slow_verify() -> bool:
            await gate.wait()
            return True

        with patch.object(
            self.manager._settings_manager, "verify_connectivity", new=_slow_verify
        ):
            self.manager.on_config_candidate()
            await self._drain(5)
            self.manager.on_config_candidate()
            self.manager.on_config_candidate()
            await self._drain(5)

            gate.set()
            await self._drain()

        self.assertEqual(
            self.service_starts["n"], 1, "去重后只应执行一次应用（当前可能并发多次）"
        )


class TestShutdownAfterDialog(ManagerFlowTestBase):
    """回归点 2

    - 关闭后不再弹窗
    """

    async def test_saved_ignored_after_shutdown(self) -> None:
        """向导已弹、用户点关闭 → 后续保存被忽略

        - 事件放行退出
        """
        self.verify_results = [False]
        await self.manager._applier.apply_config()
        self.assertEqual(len(self.force_events), 1)

        self.manager.on_shutdown_request()
        await self._drain()

        self.assertTrue(
            gui_bridge.shutdown_completed_event.is_set(), "关闭处理必须放行 GUI 退出"
        )

        self.manager.on_config_candidate()
        await self._drain()

        self.assertEqual(len(self.force_events), 1, "关闭后不得再弹向导")
        self.assertEqual(self.service_starts["n"], 0, "关闭后不得启动服务")


class TestShutdownCancel(ManagerFlowTestBase):
    """回归点 3

    - 取消关闭后必须恢复响应配置事件
    """

    async def test_cancel_restores_config_handling(self) -> None:
        """取消关闭后再保存配置应重新校验

        - 而非被永久忽略
        """
        self.verify_results = [False, False, True]

        # 进入关闭再取消
        self.manager.on_shutdown_request()
        await self._drain()
        self.manager.on_shutdown_cancelled()
        await self._drain()

        # 取消后保存配置：应正常重入校验
        self.manager.on_config_candidate()
        await self._drain()
        self.manager.on_config_candidate()
        await self._drain()
        self.manager.on_config_candidate()
        await self._drain()

        self.assertGreaterEqual(
            self.verify_calls, 1, "取消关闭后配置保存必须重新触发校验"
        )
        self.assertEqual(self.service_starts["n"], 1, "第三次校验通过应启动服务")


class TestTokenFatal(ManagerFlowTestBase):
    """回归点 7

    - token 致命错弹窗退出，proxy 连带待复查不得误退
    """

    async def _capture_notices(self):
        """挂致命通知捕获，返回 (容器, 解除函数)"""
        notices: list[tuple[str, bool]] = []
        sig = gui_bridge.request_notice

        def _cap(msg: str = "", critical: bool = False) -> None:
            notices.append((msg, critical))

        sig.connect(_cap, f"test-token-fatal-{self.id()}")
        return notices, lambda: sig._instance.disconnect(_cap)

    async def test_token_error_emits_fatal_not_setup(self) -> None:
        """proxy 通而 token 错 → 致命通知，不弹向导不启服务"""
        notices, disconnect = await self._capture_notices()
        try:
            sm = self.manager._settings_manager

            async def _token_fail() -> bool:
                sm.last_errors = {FieldKey.TOKEN: "Token 无效"}
                return False

            with patch.object(sm, "verify_connectivity", new=_token_fail):
                await self.manager._applier.apply_config()

            self.assertEqual(len(notices), 1, "token 错应弹一次致命通知")
            self.assertTrue(notices[0][1], "致命通知应标记 critical")
            self.assertEqual(len(self.force_events), 0, "token 错不得弹向导")
            self.assertEqual(self.service_starts["n"], 0, "token 错不得启动服务")
        finally:
            disconnect()

    async def test_token_error_is_fatal_whatever_it_carries(self) -> None:
        """token 报错即致命，连带代理错也不走向导

        - 代理不通时那行待复查标注由聚合侧抹掉，进到这里即真测到过
        """
        notices, disconnect = await self._capture_notices()
        try:
            sm = self.manager._settings_manager

            async def _proxy_fail() -> bool:
                sm.last_errors = {
                    FieldKey.PROXY: "代理不通",
                    FieldKey.TOKEN: "暂未检测",
                }
                return False

            with patch.object(sm, "verify_connectivity", new=_proxy_fail):
                await self.manager._applier.apply_config()

            self.assertEqual(len(notices), 1, "token 错一律走致命退出")
            self.assertEqual(len(self.force_events), 0, "致命退出不再弹向导")
        finally:
            disconnect()


class TestIdentityReset(ManagerFlowTestBase):
    """回归点 9

    - 校验通过时按对话身份决定要不要清历史
    - 没有清理入口的那轮不落基准，下一轮补上
    """

    def _stage(
        self, text: dict, owner: dict, with_reset: bool = True
    ) -> tuple[list[int], object]:
        """把正文、主人与清理入口换成可控值，交出调用记录与清理桩"""
        calls: list[int] = []

        async def _reset() -> None:
            calls.append(1)

        for patcher in (
            patch.object(
                self.manager._service_manager,
                "_history_resets",
                (_reset,) if with_reset else (),
            ),
            patch.object(_apply, "applied_persona_text", lambda: text["v"]),
            patch.object(
                _apply.config_manager,
                "get_all",
                lambda: {"chore": {"owner": owner["v"]}},
            ),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)
        return calls, _reset

    async def test_persona_body_change_clears_once(self) -> None:
        """正文换版即清，同一版再保存不重复清"""
        text, owner = {"v": "旧正文"}, {"v": "456"}
        calls, _ = self._stage(text, owner)

        await self.manager._applier.apply_config()
        self.assertEqual(calls, [], "首次应用只记基准")

        text["v"] = "新正文"
        await self.manager._applier.apply_config()
        self.assertEqual(calls, [1], "正文换版应清一次")

        await self.manager._applier.apply_config()
        self.assertEqual(calls, [1], "正文没再动不该重复清")

    async def test_owner_change_clears_even_with_same_body(self) -> None:
        """主人换了即便正文一字不动也清"""
        text, owner = {"v": "同一正文"}, {"v": "456"}
        calls, _ = self._stage(text, owner)

        await self.manager._applier.apply_config()
        owner["v"] = "789"
        await self.manager._applier.apply_config()

        self.assertEqual(calls, [1], "主人变更应清一次")

    async def test_missing_entry_retries_next_round(self) -> None:
        """插件没交清理入口时不落基准，下一轮接着清"""
        text, owner = {"v": "旧正文"}, {"v": "456"}
        calls, reset = self._stage(text, owner, with_reset=False)
        applier = self.manager._applier

        await applier.apply_config()
        text["v"] = "新正文"
        await applier.apply_config()
        self.assertEqual(calls, [], "没有入口不该假装清过")

        with patch.object(self.manager._service_manager, "_history_resets", (reset,)):
            await applier.apply_config()

        self.assertEqual(calls, [1], "入口到位即补上这次清理")


class TestFatalRouting(ManagerFlowTestBase):
    """回归点 4

    - 未预期异常经 catch_all 路由到致命通知，不再上抛杀进程
    """

    async def test_start_guard_catches_unexpected(self) -> None:
        """初始化抛未知异常 → 致命通知发出

        - 协程正常返回
        """
        fatal_texts: list[tuple[str, bool]] = []
        sig = gui_bridge.request_notice

        def _cap(msg: str = "", critical: bool = False) -> None:
            fatal_texts.append((msg, critical))

        sig.connect(_cap, f"test-fatal-{self.id()}")
        try:
            with patch.object(
                self.manager._initializer,
                "execute",
                new=_raise_value_error,
            ):
                await self.manager.start()  # 不应抛出
            self.assertEqual(len(fatal_texts), 1, "未知异常应路由致命通知")
            self.assertTrue(fatal_texts[0][1], "未知异常应标记 critical")
        finally:
            sig._instance.disconnect(_cap)


async def _raise_value_error() -> None:
    """打桩

    - 模拟未知异常穿透初始化
    """
    raise ValueError("boom")


class TestSignalIsolation(unittest.TestCase):
    """回归点 5

    - emit 一个信号不得触发其他信号的槽（历史串扰）
    """

    def test_emit_does_not_cross_fire_other_signals(self) -> None:
        """Emit 单个信号只触达本信号的槽"""
        hits: list[str] = []
        sigs = {}

        def _probe(name: str):
            def _slot(*_a) -> None:
                hits.append(name)

            return _slot

        for sig_name in (
            "config_candidate",
            "request_shutdown",
            "request_force_setup",
            "request_exit",
            "request_notice",
        ):
            wrapper = getattr(gui_bridge, sig_name)
            sigs[sig_name] = wrapper
            wrapper.connect(_probe(sig_name), f"isolation-{sig_name}")

        try:
            sigs["config_candidate"].emit()
            self.assertEqual(hits, ["config_candidate"], "信号串扰（未隔离）")
        finally:
            for wrapper in sigs.values():
                try:
                    wrapper._instance.disconnect()
                except RuntimeError:
                    pass


class TestStopPollingIsAwaited(unittest.IsolatedAsyncioTestCase):
    """回归点 6

    - 适配器 stop 是协程，必须被 await
    - 停服只等引擎收尾，放行退出的旗不在这里挂
    """

    async def test_stop_awaits_stop_polling(self) -> None:
        """Stop 必须 await 适配器 stop 协程"""
        from bot._service import BotService

        class FakeSession:
            async def close(self) -> None:
                pass

        class FakeBot:
            session = FakeSession()

        class FakeAdapter:
            bot = FakeBot()

            def __init__(self) -> None:
                self.stop_called = asyncio.Event()

            async def stop(self) -> None:
                self.stop_called.set()

        adapter = FakeAdapter()
        service = BotService(adapter)  # type: ignore[arg-type]
        service._loop = asyncio.get_running_loop()

        class _FakeThread:
            @staticmethod
            def is_alive() -> bool:
                return True

        service._thread = _FakeThread()  # type: ignore[assignment]
        service._idle_event.set()  # 引擎线程已收尾
        gui_bridge.shutdown_completed_event.clear()

        service.stop()
        for _ in range(100):
            await asyncio.sleep(0)

        self.assertTrue(
            adapter.stop_called.is_set(),
            "适配器 stop 协程必须被真正 await",
        )
        self.assertFalse(
            gui_bridge.shutdown_completed_event.is_set(),
            "停服不等收尾就放行退出",
        )

    async def test_polling_exit_sets_idle_flag(self) -> None:
        """轮询协程退出即挂上收尾完成旗"""

        class _FakeSession:
            async def close(self) -> None:
                pass

        class _FakeAdapter:
            bot = SimpleNamespace(session=_FakeSession())

            async def start(self) -> None:
                raise RuntimeError("非链路故障")

            async def stop(self) -> None:
                pass

        service = BotService(_FakeAdapter())  # type: ignore[arg-type]

        with self.assertRaises(RuntimeError):
            await service._polling_task()

        self.assertTrue(service._idle_event.is_set(), "收尾没挂上完成旗")


class _FlakyAdapter:
    """按脚本抛错的假适配器

    - 只喂 _start_polling 需要的 start 协程
    """

    def __init__(self, errors: list[Exception]) -> None:
        self._errors = errors
        self.calls = 0

    async def start(self) -> None:
        self.calls += 1
        if self._errors:
            raise self._errors.pop(0)


class TestHandshakeRetry(unittest.IsolatedAsyncioTestCase):
    """回归点 8

    - 起轮询的链路故障退避重试，不穿透成引擎线程异常
    """

    def _network_error(self) -> TelegramNetworkError:
        """构造一条链路族异常"""
        return TelegramNetworkError(method=GetMe(), message="offline")

    async def test_link_failure_retries_until_up(self) -> None:
        """断两次后起上：三次握手，协程正常返回"""
        adapter = _FlakyAdapter([self._network_error()] * 2)
        service = BotService(adapter)  # type: ignore[arg-type]
        with patch("bot._service._POLL_RETRY_DELAY", 0.0):
            await service._start_polling()
        self.assertEqual(adapter.calls, 3)

    async def test_non_link_error_propagates(self) -> None:
        """配置类异常不退避，照旧外抛给线程兜底"""
        adapter = _FlakyAdapter([ValueError("bad config")])
        service = BotService(adapter)  # type: ignore[arg-type]
        with patch("bot._service._POLL_RETRY_DELAY", 0.0):
            with self.assertRaises(ValueError):
                await service._start_polling()
        self.assertEqual(adapter.calls, 1)

    async def test_stop_event_ends_retry(self) -> None:
        """退避期间收到停服：立即收尾，不再握手"""
        adapter = _FlakyAdapter([self._network_error()])
        service = BotService(adapter)  # type: ignore[arg-type]
        task = asyncio.create_task(service._start_polling())
        await asyncio.sleep(0.2)
        service._stop_event.set()
        await asyncio.wait_for(task, timeout=2.0)
        self.assertEqual(adapter.calls, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
