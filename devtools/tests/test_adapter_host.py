# devtools/tests/test_adapter_host.py
"""适配器装载单元测试

- 齐两项的清单读出导入路径，缺项或平台认不出的整份拒收
- 有清单的平台取到四件，没清单的平台抛缺件异常
- 缺件那句取映射文案，带平台标识
- 清单表空着也进得了配置管理器
"""

import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from bot._adapter_host import _manifest as manifest_mod  # noqa: E402
from bot._adapter_host import _parts as parts_mod  # noqa: E402
from bot._managers import _settings as settings_mod  # noqa: E402
from bot.error_guard import error_guard  # noqa: E402
from core.domain import Platform  # noqa: E402
from core.dto import AdapterManifestDTO  # noqa: E402
from exceptions import AdapterMissingError  # noqa: E402
from finshin_sdk import AdapterParts  # noqa: E402
from ui import gui_bridge  # noqa: E402

_PARTS_KEYS = ("assemble", "channel_probe", "engine_preload", "diagnose")


class TestAdapterHost(unittest.TestCase):
    """清单读取、取件与缺件语义"""

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

    def _scan(self, body: str) -> dict[Platform, AdapterManifestDTO]:
        """在临时目录摆一份清单再扫一遍"""
        with tempfile.TemporaryDirectory() as tmp:
            adapters_dir = Path(tmp)
            (adapters_dir / "telegram").mkdir()
            (adapters_dir / "telegram" / "adapter.toml").write_text(
                body, encoding="utf-8"
            )
            with patch.object(manifest_mod, "_adapters_dir", lambda: adapters_dir):
                return manifest_mod.load_manifests()

    def test_full_manifest_is_read(self) -> None:
        """齐两项的清单读出导入路径

        - 清单多写一行入口模块名按未知键忽略
        """
        manifests = self._scan('platform = "tg"\nversion = "1.2.3"\nentry = "other"\n')
        manifest = manifests[Platform.TELEGRAM]
        self.assertEqual(manifest.version, "1.2.3")
        self.assertEqual(manifest.entry, "adapters.telegram.entry")

    def test_incomplete_manifest_is_dropped(self) -> None:
        """缺必填项的清单不进表"""
        self.assertEqual(self._scan('platform = "tg"\n'), {})

    def test_unknown_platform_is_dropped(self) -> None:
        """平台标识认不出的清单不进表"""
        manifests = self._scan('platform = "nope"\nversion = "1"\n')
        self.assertEqual(manifests, {})

    def test_listed_platform_returns_parts(self) -> None:
        """有清单的平台取到四件，四件都能调"""
        parts = parts_mod.parts_for(Platform.TELEGRAM)
        self.assertIsInstance(parts, AdapterParts)
        for key in _PARTS_KEYS:
            self.assertTrue(callable(getattr(parts, key)), key)

    def test_unlisted_platform_raises_missing(self) -> None:
        """没清单的平台抛缺件异常并带上平台标识"""
        with self.assertRaises(AdapterMissingError) as ctx:
            parts_mod.parts_for(Platform.QQ)
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

    def test_settings_import_does_not_take_parts(self) -> None:
        """清单表空着也进得了配置管理器

        - 抛点在探测入口调用处
        """
        with patch.object(parts_mod, "load_manifests", lambda: {}):
            importlib.reload(settings_mod)
            with self.assertRaises(AdapterMissingError):
                settings_mod._channel_probe()
