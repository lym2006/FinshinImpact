# devtools/tests/test_adapter_host.py
"""适配器装载单元测试

- 齐两项的清单读出导入路径，缺项或平台认不出的整份拒收
- 声明的依赖读出依赖表，没写即空表，写法不对的整份拒收
- 有清单的平台取到四件，没清单的平台抛缺件异常
- 清单要的接口版本比本机新即拒载，读不懂的版本串同样拒载
- 缺件那句取映射文案，带平台标识
- 启动取件被拒与未知异常都弹窗，正文不带异常原文
- 清单表空着也进得了配置管理器
- 入口模块的装配只交运行时，挂日志与注册插件归装载侧
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

from bot import _main as main_mod  # noqa: E402
from bot._adapter_host import _assemble as assemble_mod  # noqa: E402
from bot._adapter_host import _parts as parts_mod  # noqa: E402
from bot._managers import _settings as settings_mod  # noqa: E402
from bot.error_guard import error_guard  # noqa: E402
from exceptions import AdapterMissingError, AdapterOutOfDateError  # noqa: E402
from finshin_sdk import AdapterParts, BaseAdapter, PlatformAssembly  # noqa: E402
from finshin_sdk.domain import Platform  # noqa: E402
from finshin_sdk.dto import AdapterManifestDTO, PluginManifestDTO  # noqa: E402
from services import adapter_manifest as manifest_mod  # noqa: E402
from ui import gui_bridge  # noqa: E402

_PARTS_KEYS = ("assemble", "channel_probe", "engine_preload", "diagnose")


class _FakeMiddleware:
    """假日志中间件，只用来认出装载侧交来的那一只"""


class _FakeAdapter(BaseAdapter):
    """记下装载侧交来的两件，其余成员按基类要求补齐"""

    def __init__(self) -> None:
        self.sink = object()
        self.builder = lambda spec: spec
        self.attached: list[object] = []

    @property
    def platform(self) -> Platform:
        """平台标识"""
        return Platform.TELEGRAM

    @property
    def interaction(self):  # type: ignore[override]
        """交互端口"""
        return None

    @property
    def route_sink(self):  # type: ignore[override]
        """事件分发替身"""
        return self.sink

    @property
    def router_builder(self):  # type: ignore[override]
        """清单编译替身"""
        return self.builder

    def attach_middleware(self, middleware: object) -> None:
        """收下装载侧交来的日志中间件"""
        self.attached.append(middleware)

    async def start(self) -> None:
        """启动空动作"""

    async def stop(self) -> None:
        """停止空动作"""

    async def close(self) -> None:
        """收尾空动作"""

    def is_link_failure(self, exc: BaseException) -> bool:
        """连接失败判据替身"""
        return False


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
                return manifest_mod.load_adapter_manifests()

    def test_full_manifest_is_read(self) -> None:
        """齐必填项的清单读出导入路径

        - 清单多写一行入口模块名按未知键忽略
        """
        manifests = self._scan('platform = "tg"\nentry = "other"\n')
        self.assertEqual(manifests[Platform.TELEGRAM].entry, "adapters.telegram.entry")

    def test_incomplete_manifest_is_dropped(self) -> None:
        """缺必填项的清单不进表

        - 空文件与只写依赖的都不进表
        """
        self.assertEqual(self._scan(""), {})
        self.assertEqual(self._scan('deps = ["httpx"]\n'), {})

    def test_unknown_platform_is_dropped(self) -> None:
        """平台标识认不出的清单不进表"""
        manifests = self._scan('platform = "nope"\n')
        self.assertEqual(manifests, {})

    def test_declared_deps_are_read(self) -> None:
        """声明依赖的清单按顺序读出依赖表"""
        manifests = self._scan('platform = "tg"\ndeps = ["aiogram==3.29.1", "httpx"]\n')
        self.assertEqual(
            manifests[Platform.TELEGRAM].deps, ("aiogram==3.29.1", "httpx")
        )

    def test_absent_deps_reads_empty(self) -> None:
        """没写依赖的清单读出空表照样进表"""
        manifests = self._scan('platform = "tg"\n')
        self.assertEqual(manifests[Platform.TELEGRAM].deps, ())

    def test_bad_deps_drops_manifest(self) -> None:
        """依赖写法不对的清单不进表

        - 整项不是数组
        - 数组里有空串或非字符串
        """
        self.assertEqual(self._scan('platform = "tg"\ndeps = "httpx"\n'), {})
        self.assertEqual(self._scan('platform = "tg"\ndeps = ["", 3]\n'), {})

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

    def test_requires_sdk_is_read(self) -> None:
        """清单里的接口版本要求读进表，没写即空串"""
        card = self._scan('platform = "tg"\nrequires_sdk = "0.2.0"\n')
        self.assertEqual(card[Platform.TELEGRAM].requires_sdk, "0.2.0")
        bare = self._scan('platform = "tg"\n')
        self.assertEqual(bare[Platform.TELEGRAM].requires_sdk, "")

    def test_newer_requirement_refuses_before_import(self) -> None:
        """清单要的接口版本比本机新即拒载，且不碰入口模块"""
        too_new = AdapterManifestDTO(
            platform=Platform.TELEGRAM,
            deps=(),
            requires_sdk="99.0.0",
            entry="adapters.telegram.entry",
        )
        with patch.object(
            parts_mod, "load_adapter_manifests", lambda: {Platform.TELEGRAM: too_new}
        ):
            with patch.object(parts_mod, "import_module") as imported:
                with self.assertRaises(AdapterOutOfDateError) as ctx:
                    parts_mod.parts_for(Platform.TELEGRAM)
        self.assertEqual(ctx.exception.requires, "99.0.0")
        imported.assert_not_called()

    def test_unreadable_requirement_refuses(self) -> None:
        """版本串读不懂即拒载，原串交给那句人话"""
        broken = AdapterManifestDTO(
            platform=Platform.TELEGRAM,
            deps=(),
            requires_sdk="最新",
            entry="adapters.telegram.entry",
        )
        with patch.object(
            parts_mod, "load_adapter_manifests", lambda: {Platform.TELEGRAM: broken}
        ):
            with self.assertRaises(AdapterOutOfDateError):
                parts_mod.parts_for(Platform.TELEGRAM)

    def test_settings_import_does_not_take_parts(self) -> None:
        """清单表空着也进得了配置管理器

        - 抛点在探测入口调用处
        """
        with patch.object(parts_mod, "load_adapter_manifests", lambda: {}):
            importlib.reload(settings_mod)
            with self.assertRaises(AdapterMissingError):
                settings_mod._channel_probe()

    def test_startup_refusal_pops_the_notice(self) -> None:
        """启动取件被拒时那句人话上屏

        - 取件排在主窗之前，主窗的兜底还没挂上
        - 先收提示卡，再弹报错窗
        """
        popped: list[str] = []
        events: list[str] = []

        def refuse(_platform: object) -> None:
            raise AdapterOutOfDateError("tg", "9.9.9", "0.1.0")

        with (
            patch.object(main_mod, "ensure_app", lambda: object()),
            patch.object(
                main_mod,
                "show_popup",
                lambda _t, body: (popped.append(body), events.append("popup")),
            ),
            patch.object(main_mod, "parts_for", refuse),
        ):
            main = main_mod.Main(
                on_ready=None, close_wait=lambda: events.append("dismiss")
            )
            self.assertEqual(main.main(), 1)

        self.assertEqual(popped, ["这个平台的适配器要接口包 9.9.9 以上，本机是 0.1.0"])
        self.assertEqual(events, ["dismiss", "popup"])

    def test_unknown_startup_error_pops_without_details(self) -> None:
        """未知启动异常只报一句要去看日志，异常原文不上屏"""
        popped: list[str] = []

        def break_out(_platform: object) -> None:
            raise RuntimeError("内部细节不许进界面")

        with (
            patch.object(main_mod, "ensure_app", lambda: object()),
            patch.object(main_mod, "show_popup", lambda _t, body: popped.append(body)),
            patch.object(main_mod, "parts_for", break_out),
        ):
            self.assertEqual(main_mod.Main(on_ready=None).main(), 1)

        self.assertTrue(popped[0].startswith("程序启动失败，详情见日志"))
        self.assertNotIn("内部细节不许进界面", popped[0])

    def test_assemble_hands_over_runtime_only(self) -> None:
        """入口模块的装配只交运行时

        - 交出的运行时带路由挂载口、清单编译器与中间件挂载点
        - 插件报告那几栏由装载侧拼齐
        """
        runtime = parts_mod.parts_for(Platform.TELEGRAM).assemble(
            "123456:AA-test-token", None
        )
        self.assertIsInstance(runtime, BaseAdapter)
        self.assertTrue(callable(runtime.router_builder))
        self.assertTrue(callable(runtime.attach_middleware))
        self.assertTrue(hasattr(runtime, "route_sink"))

    def test_host_wires_middleware_and_plugins(self) -> None:
        """挂日志与注册插件这两步归装载侧

        - 交进注册的是这只适配器自己的挂载口与编译器
        - 装配结果由装载侧拼齐
        """
        adapter = _FakeAdapter()
        parts = AdapterParts(
            assemble=lambda token, proxy: adapter,
            channel_probe=None,  # type: ignore[arg-type]
            engine_preload=None,  # type: ignore[arg-type]
            diagnose=None,  # type: ignore[arg-type]
        )
        seen: dict[str, object] = {}
        row = PluginManifestDTO(
            name="help", module="bundled.help", title="帮助", summary=""
        )

        def register(sink: object, builder: object) -> tuple:
            """记下装载侧交来的两件"""
            seen.update(sink=sink, builder=builder)
            return ([(row, None)], (), (), {})

        with (
            patch.object(assemble_mod, "parts_for", lambda platform: parts),
            patch.object(assemble_mod, "register_plugins", register),
            patch.object(assemble_mod, "LoggingMiddleware", _FakeMiddleware),
        ):
            assembly = assemble_mod.assemble_platform(Platform.TELEGRAM, "t", None)

        self.assertIsInstance(assembly, PlatformAssembly)
        self.assertEqual(len(adapter.attached), 1)
        self.assertIsInstance(adapter.attached[0], _FakeMiddleware)
        self.assertEqual(seen["sink"], adapter.sink)
        self.assertEqual(seen["builder"], adapter.builder)
        self.assertEqual(assembly.report, [(row, None)])
