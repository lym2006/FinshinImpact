"""适配器装载单元测试

- 目录声明齐必填项的读出导入路径，缺项或认不出的整份拒收
- 已装包交出的入口点读出清单，同名平台认目录里那份
- 声明的依赖读出依赖表，没写即空表，写法不对的整份拒收
- 有清单的平台取到三件，没清单的平台抛缺件异常
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
from types import SimpleNamespace
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
from exceptions import (  # noqa: E402
    AdapterImportError,
    AdapterMissingError,
    AdapterOutOfDateError,
)
from finshin_sdk import AdapterParts, BaseAdapter, PlatformAssembly  # noqa: E402
from finshin_sdk.domain import ADAPTER_DECLARATION_FILE, Platform  # noqa: E402
from finshin_sdk.dto import AdapterManifestDTO, PluginManifestDTO  # noqa: E402
from services import adapter_manifest as manifest_mod  # noqa: E402
from ui import gui_bridge  # noqa: E402

_PARTS_KEYS = ("assemble", "channel_probe", "engine_preload")

# 交出三件的假入口件源码，形状照接口包那份 AdapterParts
_THREE_PARTS = """from finshin_sdk import AdapterParts


def parts():
    return AdapterParts(
        assemble=lambda token, proxy: None,
        channel_probe=lambda token, proxy: None,
        engine_preload=lambda token, proxy: None,
    )
"""

# 只交一只 parts 函数的假入口件，够来源日志那条用例取一次件
_ONE_PART_CALLER = "def parts(): return None"

# 入口点段默认那一条，键即平台标识
_DEFAULT_POINTS = 'tg = "fake_adapter.entry:parts"\n'


def _manifest(project: str = "", tool: str = "", points: str = _DEFAULT_POINTS) -> str:
    """拼一份适配器声明文件正文，三段各按用例要验的写法给

    - 平台标识住 [tool.finshin-adapter]，依赖与接口包版本要求住 [project].dependencies
    - 入口点段按平台标识点名入口模块，模块与属性之间用冒号
    """
    return (
        f'[project]\nname = "fake-adapter"\n{project}'
        f"[tool.finshin-adapter]\n{tool}"
        f'[project.entry-points."finshin.adapters"]\n{points}'
    )


def _fake_point(
    name: str = "tg",
    module: str = "fake_adapter.entry",
    attr: str = "parts",
    requires: tuple[str, ...] = (),
) -> SimpleNamespace:
    """一只已装包交出的入口点替件，只带读取器用到的那几项"""
    dist = SimpleNamespace(
        name="finshin-adapter-tg", version="0.1.0", requires=list(requires)
    )
    return SimpleNamespace(name=name, module=module, attr=attr, dist=dist)


class _FakeMiddleware:
    """假日志中间件，只用来认出装载侧交来的那一只"""


class _FakeAdapter(BaseAdapter):
    """记下装载侧交来的中间件，其余成员按基类要求补齐"""

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
        """在临时目录摆一份声明文件再扫一遍"""
        with tempfile.TemporaryDirectory() as tmp:
            adapters_dir = Path(tmp)
            (adapters_dir / "telegram").mkdir()
            (adapters_dir / "telegram" / ADAPTER_DECLARATION_FILE).write_text(
                body, encoding="utf-8"
            )
            # 环境里那只已装适配器不参与，否则拒收用例会被它顶绿
            with (
                patch.object(manifest_mod, "_adapters_dir", lambda: adapters_dir),
                patch.object(manifest_mod, "_installed_points", lambda: ()),
            ):
                return manifest_mod.load_adapter_manifests()

    def _install(self, source: str) -> Path:
        """在临时目录装一只假适配器件，回它所在的根目录"""
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        root = Path(holder.name)
        (root / "fake_tg").mkdir()
        (root / "fake_tg" / "__init__.py").write_text("", encoding="utf-8")
        (root / "fake_tg" / "entry.py").write_text(source, encoding="utf-8")
        sys.path.insert(0, str(root))
        self.addCleanup(sys.path.remove, str(root))
        self.addCleanup(sys.modules.pop, "fake_tg", None)
        self.addCleanup(sys.modules.pop, "fake_tg.entry", None)
        return root

    def _take(self, source: str) -> Path:
        """装着假件取一次件，回它所在的根目录"""
        root = self._install(source)
        card = AdapterManifestDTO(
            platform=Platform.TELEGRAM, deps=(), requires_sdk="", entry="fake_tg.entry"
        )
        patcher = patch.object(
            parts_mod, "load_adapter_manifests", lambda: {Platform.TELEGRAM: card}
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        return root

    def test_full_manifest_is_read(self) -> None:
        """齐必填项的声明读出入口模块名

        - 模块名取自声明的入口点段
        """
        manifests = self._scan(_manifest(tool='platform = "tg"\n'))
        self.assertEqual(manifests[Platform.TELEGRAM].entry, "fake_adapter.entry")

    def test_incomplete_manifest_is_dropped(self) -> None:
        """缺必填项的声明不进表

        - 空文件与只写依赖的都不进表
        """
        self.assertEqual(self._scan(""), {})
        self.assertEqual(
            self._scan(_manifest(project='dependencies = ["httpx"]\n')), {}
        )

    def test_unknown_platform_is_dropped(self) -> None:
        """平台标识认不出的声明不进表"""
        self.assertEqual(self._scan(_manifest(tool='platform = "nope"\n')), {})

    def test_platform_not_in_entry_points_is_dropped(self) -> None:
        """入口点段没点名本平台的声明不进表

        - 只写了别的平台那条的算它自己没交代入口
        """
        self.assertEqual(
            self._scan(
                _manifest(
                    tool='platform = "tg"\n',
                    points='qq = "fake_adapter.entry:parts"\n',
                )
            ),
            {},
        )

    def test_wrong_entry_attribute_is_dropped(self) -> None:
        """入口点冒号后不指 parts 的声明不进表"""
        self.assertEqual(
            self._scan(
                _manifest(
                    tool='platform = "tg"\n',
                    points='tg = "fake_adapter.entry:run"\n',
                )
            ),
            {},
        )

    def test_declared_deps_are_read(self) -> None:
        """声明依赖的清单按顺序读出依赖表"""
        manifests = self._scan(
            _manifest(
                project='dependencies = ["aiogram==3.29.1", "httpx"]\n',
                tool='platform = "tg"\n',
            )
        )
        self.assertEqual(
            manifests[Platform.TELEGRAM].deps, ("aiogram==3.29.1", "httpx")
        )

    def test_absent_deps_reads_empty(self) -> None:
        """没写依赖的声明读出空表照样进表"""
        manifests = self._scan(_manifest(tool='platform = "tg"\n'))
        self.assertEqual(manifests[Platform.TELEGRAM].deps, ())

    def test_bad_deps_drops_manifest(self) -> None:
        """依赖写法不对的声明不进表

        - 整项不是数组
        - 数组里有空串或非字符串
        """
        self.assertEqual(
            self._scan(
                _manifest(project='dependencies = "httpx"\n', tool='platform = "tg"\n')
            ),
            {},
        )
        self.assertEqual(
            self._scan(
                _manifest(project='dependencies = ["", 3]\n', tool='platform = "tg"\n')
            ),
            {},
        )

    def test_listed_platform_returns_parts(self) -> None:
        """有清单的平台取到三件，三件都能调"""
        self._take(_THREE_PARTS)
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

    def test_sdk_requires_read_from_deps(self) -> None:
        """接口包版本要求从依赖声明里整条读，没写即空串"""
        card = self._scan(
            _manifest(
                project='dependencies = ["aiogram", "finshin-sdk>=0.2.0"]\n',
                tool='platform = "tg"\n',
            )
        )
        self.assertEqual(card[Platform.TELEGRAM].requires_sdk, ">=0.2.0")

        ranged = self._scan(
            _manifest(
                project='dependencies = ["finshin-sdk>=0.2.0,<0.3.0"]\n',
                tool='platform = "tg"\n',
            )
        )
        self.assertEqual(ranged[Platform.TELEGRAM].requires_sdk, ">=0.2.0,<0.3.0")

        bare = self._scan(_manifest(tool='platform = "tg"\n'))
        self.assertEqual(bare[Platform.TELEGRAM].requires_sdk, "")

    def test_newer_requirement_refuses_before_import(self) -> None:
        """清单要的接口版本比本机新即拒载，入口模块的导入没发生"""
        too_new = AdapterManifestDTO(
            platform=Platform.TELEGRAM,
            deps=(),
            requires_sdk=">=99.0.0",
            entry="standalone_tg.entry",
        )
        with patch.object(
            parts_mod, "load_adapter_manifests", lambda: {Platform.TELEGRAM: too_new}
        ):
            with patch.object(parts_mod, "import_module") as imported:
                with self.assertRaises(AdapterOutOfDateError) as ctx:
                    parts_mod.parts_for(Platform.TELEGRAM)
        self.assertEqual(ctx.exception.requires, ">=99.0.0")
        imported.assert_not_called()

    def test_sdk_over_ceiling_refuses_before_import(self) -> None:
        """本机接口包高出清单写的上限即拒载，入口模块的导入没发生"""
        too_old = AdapterManifestDTO(
            platform=Platform.TELEGRAM,
            deps=(),
            requires_sdk="<0.0.1",
            entry="standalone_tg.entry",
        )
        with patch.object(
            parts_mod, "load_adapter_manifests", lambda: {Platform.TELEGRAM: too_old}
        ):
            with patch.object(parts_mod, "import_module") as imported:
                with self.assertRaises(AdapterOutOfDateError) as ctx:
                    parts_mod.parts_for(Platform.TELEGRAM)
        self.assertEqual(ctx.exception.requires, "<0.0.1")
        imported.assert_not_called()

    def test_external_adapter_importing_body_is_refused(self) -> None:
        """外部适配器引了本体内部即拒载，入口模块的导入没发生"""
        offender = AdapterManifestDTO(
            platform=Platform.TELEGRAM,
            deps=(),
            requires_sdk="",
            entry="late_bundled_tg.entry",
        )
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        root = Path(holder.name)
        (root / "late_bundled_tg").mkdir()
        (root / "late_bundled_tg" / "__init__.py").write_text("", encoding="utf-8")
        (root / "late_bundled_tg" / "entry.py").write_text(
            "from utils import get_logger", encoding="utf-8"
        )
        sys.path.insert(0, str(root))
        self.addCleanup(sys.path.remove, str(root))
        sys.modules.pop("late_bundled_tg", None)
        self.addCleanup(sys.modules.pop, "late_bundled_tg", None)
        self.addCleanup(sys.modules.pop, "late_bundled_tg.entry", None)

        with (
            patch.object(
                parts_mod,
                "load_adapter_manifests",
                lambda: {Platform.TELEGRAM: offender},
            ),
            patch.object(parts_mod, "import_module") as imported,
        ):
            with self.assertRaises(AdapterImportError) as ctx:
                parts_mod.parts_for(Platform.TELEGRAM)
        self.assertEqual(ctx.exception.target, "utils")
        self.assertEqual(ctx.exception.where, "entry.py:1")
        imported.assert_not_called()

    def test_unreadable_requirement_refuses(self) -> None:
        """版本串读不懂即拒载，原串交给那句人话"""
        broken = AdapterManifestDTO(
            platform=Platform.TELEGRAM,
            deps=(),
            requires_sdk="最新",
            entry="standalone_tg.entry",
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
        - 版本不合只弹窗，不开面板
        """
        popped: list[str] = []
        events: list[str] = []

        def refuse(_platform: object) -> None:
            raise AdapterOutOfDateError("tg", ">=9.9.9", "0.1.0")

        with (
            patch.object(main_mod, "ensure_app", lambda: object()),
            patch.object(
                main_mod,
                "show_popup",
                lambda _t, body: (popped.append(body), events.append("popup")),
            ),
            patch.object(
                main_mod,
                "open_platform_dialog",
                lambda _parent=None: events.append("panel"),
            ),
            patch.object(main_mod, "parts_for", refuse),
        ):
            main = main_mod.Main(
                on_ready=None, close_wait=lambda: events.append("dismiss")
            )
            self.assertEqual(main.main(), 1)

        self.assertEqual(popped, ["这个平台的适配器要接口包 >=9.9.9，本机是 0.1.0"])
        self.assertEqual(events, ["dismiss", "popup"])

    def test_missing_adapter_opens_the_panel(self) -> None:
        """缺件那条报错窗关掉即开面板

        - 面板是那句之外的唯一下一步
        - 顺序是先说原因再开面板
        """
        popped: list[str] = []
        events: list[str] = []

        def refuse(_platform: object) -> None:
            raise AdapterMissingError("tg")

        with (
            patch.object(main_mod, "ensure_app", lambda: object()),
            patch.object(
                main_mod,
                "show_popup",
                lambda _t, body: (popped.append(body), events.append("popup")),
            ),
            patch.object(
                main_mod,
                "open_platform_dialog",
                lambda _parent=None: events.append("panel"),
            ),
            patch.object(main_mod, "parts_for", refuse),
        ):
            main = main_mod.Main(
                on_ready=None, close_wait=lambda: events.append("dismiss")
            )
            self.assertEqual(main.main(), 1)

        self.assertIn("这个平台的适配器还没装：tg", popped[0])
        self.assertIn("装完请重新打开本程序", popped[0])
        self.assertEqual(events, ["dismiss", "popup", "panel"])

    def test_unknown_startup_error_pops_with_one_line_detail(self) -> None:
        """未知启动异常把类名与消息那一行写上屏

        - 调用链不落屏，落调试日志
        """
        popped: list[str] = []

        def break_out(_platform: object) -> None:
            raise RuntimeError("缺了某个模块")

        with (
            patch.object(main_mod, "ensure_app", lambda: object()),
            patch.object(main_mod, "show_popup", lambda _t, body: popped.append(body)),
            patch.object(main_mod, "parts_for", break_out),
        ):
            self.assertEqual(main_mod.Main(on_ready=None).main(), 1)

        self.assertIn("RuntimeError: 缺了某个模块", popped[0])
        self.assertNotIn("Traceback", popped[0])

    def test_taken_adapter_logs_its_source(self) -> None:
        """取到的适配器把来源路径落到调试日志

        - 拆仓之后同一条日志是用户自查装件对不对的唯一线索
        """
        root = self._take(_ONE_PART_CALLER)

        with self.assertLogs("Bot.Mgr.Adapter", level="DEBUG") as captured:
            parts_mod.parts_for(Platform.TELEGRAM)
        message = captured.records[0].getMessage()
        self.assertIn(str(root), message)
        self.assertIn("entry.py", message)

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


class TestInstalledSource(unittest.TestCase):
    """已装包那一路的发现"""

    def test_installed_manifest_is_read(self) -> None:
        """目录不在场时，已装包交出的入口点读成清单

        - 平台标识取入口点的名，入口模块取值的冒号前段
        - 依赖取包元数据声明的顶层依赖
        - 接口包版本要求也从这串依赖里读
        """
        with (
            patch.object(manifest_mod, "_adapters_dir", lambda: None),
            patch.object(
                manifest_mod,
                "_installed_points",
                lambda: (
                    _fake_point(requires=("aiogram==3.29.1", "finshin-sdk>=0.2.0")),
                ),
            ),
        ):
            manifests = manifest_mod.load_adapter_manifests()

        self.assertEqual(manifests[Platform.TELEGRAM].entry, "fake_adapter.entry")
        self.assertEqual(
            manifests[Platform.TELEGRAM].deps, ("aiogram==3.29.1", "finshin-sdk>=0.2.0")
        )
        self.assertEqual(manifests[Platform.TELEGRAM].requires_sdk, ">=0.2.0")

    def test_directory_wins_over_installed(self) -> None:
        """两路同时报出这一平台时认目录里那份

        - 开发机上 pip 装过同名适配器，改的源码该当场生效
        """
        body = _manifest(
            tool='platform = "tg"\n', points='tg = "dir_adapter.entry:parts"\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            adapters_dir = Path(tmp)
            (adapters_dir / "telegram").mkdir()
            (adapters_dir / "telegram" / ADAPTER_DECLARATION_FILE).write_text(
                body, encoding="utf-8"
            )
            with (
                patch.object(manifest_mod, "_adapters_dir", lambda: adapters_dir),
                patch.object(
                    manifest_mod, "_installed_points", lambda: (_fake_point(),)
                ),
            ):
                manifests = manifest_mod.load_adapter_manifests()

        self.assertEqual(manifests[Platform.TELEGRAM].entry, "dir_adapter.entry")

    def test_wrong_attribute_on_installed_is_dropped(self) -> None:
        """已装包的入口点不指 parts 即不进表"""
        with (
            patch.object(manifest_mod, "_adapters_dir", lambda: None),
            patch.object(
                manifest_mod,
                "_installed_points",
                lambda: (_fake_point(attr="run"),),
            ),
        ):
            self.assertEqual(manifest_mod.load_adapter_manifests(), {})
