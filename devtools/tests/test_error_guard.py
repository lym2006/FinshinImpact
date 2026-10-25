# devtools/tests/test_error_guard.py
"""error_guard 装饰器单元测试

- fatal 异常走 request_notice(critical=True) 且不上抛
- 可恢复 ConfigError 走 request_force_setup 且不上抛
- 非 BotError 原样抛出
- async 函数形态同样生效
"""

import asyncio
import sys
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from bot.error_guard import error_guard  # noqa: E402
from exceptions import (  # noqa: E402
    ConfigError,
    ConfigInputError,
    ConfigMissingError,
    TokenError,
)
from ui import gui_bridge  # noqa: E402


class TestErrorGuard(unittest.TestCase):
    """error_guard 路由行为"""

    def setUp(self) -> None:
        """复位关闭标志并记录信号"""
        gui_bridge._is_shutdown_pending = False
        self.received: dict = {}
        gui_bridge.request_notice.connect(
            lambda msg, critical: self.received.update(fatal=(msg, critical)),
            tag="test-fatal",
        )
        gui_bridge.request_force_setup.connect(
            lambda errors: self.received.update(setup=errors), tag="test-setup"
        )

    def tearDown(self) -> None:
        """摘除测试槽避免泄漏到后续用例"""
        gui_bridge.request_notice.disconnect(tag="test-fatal")
        gui_bridge.request_force_setup.disconnect(tag="test-setup")

    def test_fatal_routes_to_fatal_dialog(self) -> None:
        """致命异常路由致命弹窗

        - 发 request_notice 且 critical 为真
        - 不上抛异常
        """

        @error_guard("测试")
        def boom() -> None:
            raise ConfigInputError()

        boom()
        self.assertIn("fatal", self.received)
        self.assertNotIn("setup", self.received)

    def test_recoverable_routes_to_setup(self) -> None:
        """可恢复配置异常发 request_force_setup 且不上抛"""

        @error_guard("测试")
        def boom() -> None:
            raise ConfigError(proxy="x")

        boom()
        self.assertIn("setup", self.received)
        self.assertNotIn("fatal", self.received)

    def test_path_missing_carries_field_error(self) -> None:
        """缺键异常发向导时带字段键与必填文案

        - 供面板标红
        """
        from exceptions import ConfigPathMissingError

        @error_guard("测试")
        def boom() -> None:
            raise ConfigPathMissingError("ai.new_key", "new_key")

        boom()
        self.assertEqual(list(self.received["setup"]), ["new_key"])
        self.assertIn("必填", self.received["setup"]["new_key"])

    def test_missing_section_error_uses_path_tail(self) -> None:
        """整段缺失场景

        - 字段键取点路径尾段
        """

        from exceptions import ConfigPathMissingError

        @error_guard("测试")
        def boom() -> None:
            raise ConfigPathMissingError("ai.model_name", "ai")

        boom()
        self.assertEqual(list(self.received["setup"]), ["model_name"])

    def test_connectivity_routes_to_setup(self) -> None:
        """连接性异常走向导信号"""

        @error_guard("测试")
        def boom() -> None:
            raise TokenError()

        boom()
        self.assertIn("setup", self.received)

    def test_plain_exception_propagates(self) -> None:
        """非 BotError 原样上抛"""

        @error_guard("测试")
        def boom() -> None:
            raise ValueError("other")

        with self.assertRaises(ValueError):
            boom()

    def test_async_coroutine_guarded(self) -> None:
        """协程函数形态

        - 异常被接住路由
        """
        loop = asyncio.new_event_loop()

        @error_guard("测试")
        async def boom() -> None:
            raise ConfigError(proxy="y")

        try:
            loop.run_until_complete(boom())
        finally:
            loop.close()
        self.assertIn("setup", self.received)

    def test_shutdown_pending_suppresses_all(self) -> None:
        """关闭流程中全部静默吞掉

        - 不发任何信号
        """
        gui_bridge._is_shutdown_pending = True

        @error_guard("测试")
        def boom() -> None:
            raise ConfigMissingError()

        boom()
        self.assertEqual(self.received, {})

    def test_catch_all_routes_unknown_as_fatal(self) -> None:
        """catch_all 模式

        - 非 BotError 按致命路由
        """

        @error_guard("测试", catch_all=True)
        def boom() -> None:
            raise ValueError("unexpected")

        boom()
        self.assertIn("fatal", self.received)

    def test_reraise_emits_and_propagates(self) -> None:
        """重抛模式

        - 发信号后异常继续上抛
        """

        @error_guard("测试", reraise=True)
        def boom() -> None:
            raise ConfigError(proxy="z")

        with self.assertRaises(ConfigError):
            boom()
        self.assertIn("setup", self.received)


if __name__ == "__main__":
    unittest.main(verbosity=2)
