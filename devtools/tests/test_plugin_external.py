# devtools/tests/test_plugin_external.py
"""外部插件目录装载的单元测试

- 装载认两根：随包树在前，项目根的 plugins_installed 在后
- 外部插件的导入路径带外部顶层包名，目录内部的相对引用走得通
- 同名插件以先读到的根为准，随包压住外部
- 外部目录不存在时只剩随包一根
- 插件交出的一切按契约收到：清单字段、路由、常驻协程、任务处理、时机订阅
- 权限档对不上与缺清单的插件记失败，不混进成功行
"""

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

from core.domain import (  # noqa: E402
    INSTALLED_PLUGINS_NAME,
    PLUGINS_PKG,
    HelpKey,
    ManifestKey,
    PlatformTiming,
    PluginClaim,
    TaskKind,
    resolve_claims,
)
from exceptions import PluginRoleError, PluginSpecError  # noqa: E402
from services.env_setup import deps_manifest  # noqa: E402
from utils.plugin import _manifest, _register  # noqa: E402

_MANIFEST = 'name = "{name}"\ntitle = "{title}"\nsummary = "外部目录装载用例"\n'
# 清单里的命令声明，读侧按它做命令名抢占判定
_COMMAND = '\n[[help]]\nsection = "样例"\n\n[[help.commands]]\ncmd = "{cmd}"\ndesc = "看一眼"\n'
# 入口引同目录的另一只文件，导入走不通即红
_ENTRY = """
from ._inner import ROUTE

spec = ROUTE
"""
_INNER = """
from core.domain import PluginRoute, PluginSpec


async def _never(raw: object, ctx: object) -> bool:
    \"\"\"永不命中\"\"\"
    return False


async def _drop(raw: object, ctx: object) -> None:
    \"\"\"接管即吞掉\"\"\"


ROUTE = PluginSpec(routes=(PluginRoute(_never, _drop),))
"""

# 交出全套件的清单文本，role 为命令声明的权限档
_CONTRACT_MANIFEST = """
name = "demo"
title = "契约样例"
summary = "外部插件交出的那一套件"
deps = ["httpx==0.28.1"]
assets = ["playwright chromium-headless-shell"]

[[help]]
section = "样例"

[[help.commands]]
cmd = "ping"
desc = "回一声"
flags = []
role = "{role}"
"""
_CONTRACT_ENTRY = '''
from core.domain import (
    PlatformTiming,
    PluginRoute,
    PluginSpec,
    PluginTiming,
    TaskHandler,
    TaskKind,
)


async def _hit(raw: object, ctx: object) -> bool:
    """接管这条事件"""
    return True


async def _pong(raw: object, ctx: object) -> None:
    """回一声"""


async def _beat() -> None:
    """起停期间常驻"""


async def _task(ctx: object) -> None:
    """处理一条任务"""


async def _on_call(capability: object) -> None:
    """应平台召唤"""


spec = PluginSpec(
    routes=(PluginRoute(_hit, _pong),),
    backgrounds=(_beat,),
    task_handlers=(TaskHandler(kind=TaskKind.CHAT, run=_task),),
    timings=(PluginTiming(PlatformTiming.BEFORE_ENGINE_RUN, _on_call),),
)
'''
# 陪跑一只必成功的插件，另两只失败时才轮不到整体上抛
_MATE_ENTRY = "from core.domain import PluginSpec\n\nspec = PluginSpec()\n"


def _write_plugin(
    root: Path,
    name: str,
    title: str,
    sources: dict[str, str] | None = None,
    commands: tuple[str, ...] = (),
) -> None:
    """在根目录下摆一只带清单的插件目录

    - sources 为空只交清单，用于只看读取的用例
    - commands 往清单里补命令声明，读侧据此做抢占判定
    """
    plugin_dir = root / name
    plugin_dir.mkdir(parents=True)
    text = _MANIFEST.format(name=name, title=title)
    for cmd in commands:
        text += _COMMAND.format(cmd=cmd)
    (plugin_dir / "plugin.toml").write_text(text, encoding="utf-8")
    for file_name, body in (sources or {}).items():
        (plugin_dir / file_name).write_text(body, encoding="utf-8")


class _FakeSink:
    """只记下挂上来的路由的挂载口"""

    def __init__(self) -> None:
        self.routers: list[object] = []

    def include_router(self, router: object) -> None:
        self.routers.append(router)


class ExternalRootCase(unittest.TestCase):
    """两根目录的公共脚手架：随包一根、外部一根，全在临时目录"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.bundled = base / PLUGINS_PKG
        self.bundled.mkdir()
        self.installed = base / INSTALLED_PLUGINS_NAME
        self.installed.mkdir()
        self.state = base / "plugins.toml"
        self.addCleanup(self._forget_modules)

        for name, directory in (
            ("_bundled_dir", self.bundled),
            ("_installed_dir", self.installed),
        ):
            patcher = patch.object(_manifest, name, lambda path=directory: path)
            patcher.start()
            self.addCleanup(patcher.stop)

    def _forget_modules(self) -> None:
        """摘掉这次装载挂进 sys.modules 的外部插件包"""
        pkg = INSTALLED_PLUGINS_NAME
        for name in [k for k in sys.modules if k.split(".", 1)[0] == pkg]:
            del sys.modules[name]

    def _enable_installed(self) -> None:
        """把外部目录里的插件全写进启用集"""
        names = [path.name for path in sorted(self.installed.iterdir())]
        self.state.write_text(
            "enabled = [{}]\n".format(", ".join(f'"{n}"' for n in names)),
            encoding="utf-8",
        )


class TestExternalRootReads(ExternalRootCase):
    """清单读取：两根都扫，同名定档"""

    def test_external_manifest_gets_external_module(self) -> None:
        """外部目录的插件进表，导入路径带外部顶层包名

        - 这条红了说明外部目录没进根表，或包名没按目录拼
        """
        _write_plugin(self.bundled, "inner", "随包")
        _write_plugin(self.installed, "outer", "外部")
        self._enable_installed()

        picked = _manifest.enabled_manifests(self.state)

        self.assertEqual(
            [(m.name, m.module) for m in picked],
            [("outer", f"{INSTALLED_PLUGINS_NAME}.outer")],
        )

    def test_bundled_root_wins_same_name(self) -> None:
        """同名插件两只都在盘上时读进随包那只

        - 这条红了说明后扫的根覆盖了先扫的，外部插件会顶掉随包件
        """
        _write_plugin(self.bundled, "dup", "随包")
        _write_plugin(self.installed, "dup", "外部")
        self._enable_installed()

        picked = _manifest.enabled_manifests(self.state)

        self.assertEqual(
            [(m.title, m.module) for m in picked], [("随包", f"{PLUGINS_PKG}.dup")]
        )

    def test_installed_name_clashing_bundled_table_never_loads(self) -> None:
        """外部插件改名成随包表里的名字也装不起来，写进启用集也不放行

        - 根表顺序换成外部在前，挡它的必须是判据而不是扫描运气
        """
        _write_plugin(self.bundled, "help", "随包")
        _write_plugin(self.installed, "help", "改名顶替")
        self._enable_installed()
        patcher = patch.object(
            _manifest,
            "_plugins_roots",
            lambda: [
                (self.installed, INSTALLED_PLUGINS_NAME),
                (self.bundled, PLUGINS_PKG),
            ],
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        picked = _manifest.enabled_manifests(self.state)

        self.assertEqual(
            [(m.title, m.module) for m in picked], [("随包", f"{PLUGINS_PKG}.help")]
        )

    def test_name_clash_leaves_command_claim_out_of_play(self) -> None:
        """名字撞随包件时命令撞不撞结果一样，命令那层压根不参与判定

        - 这条红了说明名字判据挪到了命令判定之后，外部声明的命令能把随包件禁掉
        - 装载侧只留随包那只，面板侧读到的行也只有随包那一份
        """
        _write_plugin(self.bundled, "help", "随包", commands=("status",))
        _write_plugin(self.installed, "help", "改名顶替", commands=("status",))
        self._enable_installed()
        patcher = patch.object(
            _manifest,
            "_plugins_roots",
            lambda: [
                (self.installed, INSTALLED_PLUGINS_NAME),
                (self.bundled, PLUGINS_PKG),
            ],
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        picked = _manifest.enabled_manifests(self.state)

        self.assertEqual(
            [(m.title, m.module) for m in picked], [("随包", f"{PLUGINS_PKG}.help")]
        )

        rows = deps_manifest.load_manifests([self.bundled, self.installed])
        claims = [
            PluginClaim(
                name=row[ManifestKey.NAME],
                commands=tuple(cmd for cmd, _ in row[HelpKey.COMMANDS]),
            )
            for row in rows
        ]
        allowed, conflicts = resolve_claims(claims, frozenset({"help"}))

        self.assertEqual(allowed, frozenset({"help"}))
        self.assertEqual(conflicts, {})

    def test_absent_external_dir_leaves_one_root(self) -> None:
        """外部目录不存在时根表只剩随包

        - 这条红了说明不存在的目录也进了表
        """
        self.installed.rmdir()

        roots = [path for path, _ in _manifest._plugins_roots()]

        self.assertEqual(roots, [self.bundled])


class TestExternalRootImports(ExternalRootCase):
    """真导入：外部插件按文件路径挂成独立包后装得起来"""

    def test_external_plugin_imports_with_relative_ref(self) -> None:
        """插件目录内部的相对引用走得通，注册记成功

        - 这条红了说明外部目录没挂上顶层包，插件里的 from ._inner import 当场断
        """
        _write_plugin(
            self.installed,
            "demo",
            "外部样例",
            {"__init__.py": _ENTRY, "_inner.py": _INNER},
        )
        self._enable_installed()
        manifests = _manifest.enabled_manifests(self.state)
        sink = _FakeSink()

        with patch.object(_register, "_resolve_plugins", lambda: manifests):
            report, *_ = _register.register_plugins(sink, lambda spec: spec)

        self.assertEqual([(m.name, error) for m, error in report], [("demo", None)])
        self.assertEqual(len(sink.routers), 1)

    def test_mount_points_at_external_dir(self) -> None:
        """外部顶层包挂的是那个目录本身

        - 这条红了说明搜索位置没写对，插件目录寻不到址
        """
        _manifest._plugins_roots()

        mounted = sys.modules[INSTALLED_PLUGINS_NAME].__path__

        self.assertEqual(list(mounted), [str(self.installed)])


class TestExternalContract(ExternalRootCase):
    """契约闸门：外部插件交出的一切从盘上收到装载侧"""

    def _register_installed(self, entries: dict[str, str], manifest: str) -> tuple:
        """按给定入口跑一轮注册，回清单序列、注册结果与挂上来的路由

        - 同时陪跑一只必成功的插件，单只失败才轮不到整体上抛
        """
        demo = self.installed / "demo"
        demo.mkdir()
        (demo / "plugin.toml").write_text(manifest, encoding="utf-8")
        for file_name, body in entries.items():
            (demo / file_name).write_text(body, encoding="utf-8")

        mate = self.installed / "mate"
        mate.mkdir()
        (mate / "plugin.toml").write_text(
            _MANIFEST.format(name="mate", title="陪跑"), encoding="utf-8"
        )
        (mate / "__init__.py").write_text(_MATE_ENTRY, encoding="utf-8")
        self._enable_installed()

        manifests = _manifest.enabled_manifests(self.state)
        sink = _FakeSink()
        with patch.object(_register, "_resolve_plugins", lambda: manifests):
            result = _register.register_plugins(sink, lambda spec: spec)

        return manifests, result, sink

    def test_every_declared_piece_arrives(self) -> None:
        """清单字段、路由、协程、任务处理与时机订阅一并收到

        - 这条红了说明交出的形状改了，照这份写的外部插件装不上
        """
        manifests, (report, backgrounds, handlers, timings), sink = (
            self._register_installed(
                {"__init__.py": _CONTRACT_ENTRY},
                _CONTRACT_MANIFEST.format(role="member"),
            )
        )
        demo = manifests[0]

        self.assertEqual(demo.module, f"{INSTALLED_PLUGINS_NAME}.demo")
        self.assertEqual(demo.deps, ("httpx==0.28.1",))
        self.assertEqual(demo.assets, ("playwright chromium-headless-shell",))
        self.assertEqual(
            [(m.name, error) for m, error in report], [("demo", None), ("mate", None)]
        )
        self.assertEqual(len(sink.routers[0].routes), 1)
        self.assertEqual(len(backgrounds), 1)
        self.assertEqual(handlers[0].kind, TaskKind.CHAT)
        self.assertEqual(list(timings), [PlatformTiming.BEFORE_ENGINE_RUN])

    def test_role_mismatch_recorded_as_failure(self) -> None:
        """清单写的权限档与路由上的守卫对不上即记权限错

        - 这条红了说明声明与拦截脱钩也照样放行
        """
        _, (report, _, _, _), _ = self._register_installed(
            {"__init__.py": _CONTRACT_ENTRY}, _CONTRACT_MANIFEST.format(role="owner")
        )

        self.assertIsInstance(report[0][1], PluginRoleError)
        self.assertIsNone(report[1][1])

    def test_spec_missing_recorded_as_failure(self) -> None:
        """插件没交出清单即记清单缺失

        - 这条红了说明空壳插件也算装载成功
        """
        _, (report, _, _, _), _ = self._register_installed(
            {"__init__.py": "value = 1\n"}, _CONTRACT_MANIFEST.format(role="member")
        )

        self.assertIsInstance(report[0][1], PluginSpecError)


if __name__ == "__main__":
    unittest.main()
