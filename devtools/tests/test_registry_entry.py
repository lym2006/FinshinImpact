# devtools/tests/test_registry_entry.py
"""平台取件口单元测试

- 已登记的平台取到装配件，没登记的平台抛缺件异常
- 缺件那句取映射文案，带平台标识
- 登记表空着也进得了配置管理器
"""

import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from bot import _registry as registry  # noqa: E402
from bot._managers import _settings as settings_mod  # noqa: E402
from bot.error_guard import error_guard  # noqa: E402
from core.domain import Platform  # noqa: E402
from exceptions import AdapterMissingError  # noqa: E402
from ui import gui_bridge  # noqa: E402


class TestRegistryEntry(unittest.TestCase):
    """取件口与缺件语义"""

    def setUp(self) -> None:
        """复位关闭标志并记录通知信号"""
        gui_bridge._is_shutdown_pending = False
        self.received: dict = {}
        gui_bridge.request_notice.connect(
            lambda msg, critical: self.received.update(fatal=(msg, critical)),
            tag="test-adapter-notice",
        )

    def tearDown(self) -> None:
        """摘除测试槽避免泄漏到后续用例"""
        gui_bridge.request_notice.disconnect(tag="test-adapter-notice")

    def test_registered_platform_returns_entry(self) -> None:
        """登记过的平台取到装配件"""
        entry = registry.entry_for(Platform.TELEGRAM)
        self.assertIs(entry, registry._ENTRIES[Platform.TELEGRAM])

    def test_unregistered_platform_raises_missing(self) -> None:
        """没登记的平台抛缺件异常并带上平台标识"""
        with self.assertRaises(AdapterMissingError) as ctx:
            registry.entry_for(Platform.QQ)
        self.assertEqual(ctx.exception.platform, "qq")

    def test_missing_notice_uses_mapped_text(self) -> None:
        """缺件走守卫路由时面板那句是映射文案

        - 带平台标识
        - 不是异常类名
        """

        @error_guard("Bot 启动")
        def assemble() -> None:
            raise AdapterMissingError(Platform.QQ)

        assemble()
        msg, critical = self.received["fatal"]
        self.assertTrue(critical)
        self.assertIn("这个平台的适配器还没装：qq", msg)
        self.assertNotIn("AdapterMissingError", msg)

    def test_settings_import_does_not_take_entry(self) -> None:
        """登记表空着也进得了配置管理器

        - 抛点在探测入口调用处
        """
        with patch.object(registry, "_ENTRIES", {}):
            importlib.reload(settings_mod)
            with self.assertRaises(AdapterMissingError):
                settings_mod._channel_probe()
