"""插件清单恒启用与档位的单元测试

- 清单只认 name/title/summary/deps/assets/help
- 恒启用与加载档位来自随包表，多写的键按未知键忽略
- 引导期精简实现与运行期读取在这两条上一致
- 引导期根表认外部目录，同名插件以随包那行为准
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from finshin_sdk.domain import (  # noqa: E402
    INSTALLED_PLUGINS_NAME,
    INSTALLED_PLUGINS_PKG,
    PLUGINS_PKG,
)
from services.env_setup import deps_manifest  # noqa: E402
from utils.plugin import _manifest  # noqa: E402

# 表外插件多写两个本体不认的键，读取侧按未知键忽略
_MANIFEST = """
name = "{name}"
title = "{name}"
summary = "外部插件"
always = true
weight = 0
deps = []
assets = []
"""


def _write(root: Path, name: str) -> None:
    """在目录下造一份多写键的清单"""
    target = root / name / "plugin.toml"
    target.parent.mkdir(parents=True)
    target.write_text(_MANIFEST.format(name=name), encoding="utf-8")


_TITLED_MANIFEST = """
name = "{name}"
title = "{title}"
summary = "外部插件"
deps = []
assets = []
"""


def _write_titled(root: Path, name: str, title: str) -> None:
    """在目录下造一份指定标题的清单"""
    target = root / name / "plugin.toml"
    target.parent.mkdir(parents=True)
    target.write_text(_TITLED_MANIFEST.format(name=name, title=title), encoding="utf-8")


_DEPENDENCY = """
[project]
name = "{name}"
version = "0"
dependencies = ["markdown==3.10.2"]
"""

# 一份外部插件的清单，deps 那行按新口径属未知键
_ECHO_MANIFEST = (
    'name = "echo"\ntitle = "回声"\nsummary = "外部插件"\ndeps = ["不该读"]\n'
)


def _write_dependency(root: Path, name: str) -> None:
    """在外部插件目录里补一份只交代依赖的声明"""
    target = root / name / "pyproject.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_DEPENDENCY.format(name=name), encoding="utf-8")


class TestEnabledOrder(unittest.TestCase):
    """运行期读取：随包表定恒启用与档位"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        for name in ("extra", "help", "AI"):
            _write(self.root, name)
        patcher = patch.object(
            _manifest, "_plugins_roots", lambda: [(self.root, "bundled")]
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_only_bundled_enabled_without_state(self) -> None:
        """清单自称恒启用不算数，未勾选就不启用"""
        picked = _manifest.enabled_manifests(self.root / "plugins.toml")

        self.assertEqual([m.name for m in picked], ["help", "AI"])

    def test_unknown_keys_not_loaded(self) -> None:
        """读回来的清单对象上没有那两个键"""
        picked = _manifest.enabled_manifests(self.root / "plugins.toml")

        self.assertFalse(hasattr(picked[0], "always"))
        self.assertFalse(hasattr(picked[0], "weight"))

    def test_external_between_bundled(self) -> None:
        """表外插件一律常规档，排在最先档之后最后档之前"""
        state = self.root / "plugins.toml"
        state.write_text('enabled = ["extra"]\n', encoding="utf-8")

        picked = _manifest.enabled_manifests(state)

        self.assertEqual([m.name for m in picked], ["help", "extra", "AI"])


class TestGuideRead(unittest.TestCase):
    """引导期精简实现：多写的键同样不认"""

    def test_unknown_keys_dropped_and_table_orders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("extra", "help", "AI"):
                _write(root, name)

            rows = deps_manifest.load_manifests([(root, PLUGINS_PKG)])

            self.assertEqual([row["name"] for row in rows], ["AI", "help", "extra"])
            self.assertFalse({"always", "weight"} & set(rows[0]))

    def test_bundled_grouped_before_external(self) -> None:
        """随包表里的三只成组在前，表外的名字再靠前也不插进来"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("aardvark", "help", "grant", "AI"):
                _write(root, name)

            rows = deps_manifest.load_manifests([(root, PLUGINS_PKG)])

            self.assertEqual(
                [row["name"] for row in rows], ["AI", "grant", "help", "aardvark"]
            )

    def test_groups_order_by_pinyin_of_title(self) -> None:
        """两组组内都按面板上那列显示名的拼音序

        - 档位表只管命令抢占先后，行序另按显示名排
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            titled = (
                ("help", "权限授权"),
                ("grant", "AI 对话"),
                ("ping_a", "帮助"),
                ("ping_b", "撞名甲"),
            )
            for name, title in titled:
                _write_titled(root, name, title)

            rows = deps_manifest.load_manifests([(root, PLUGINS_PKG)])

            self.assertEqual(
                [row["title"] for row in rows],
                ["AI 对话", "权限授权", "帮助", "撞名甲"],
            )


class TestGuideRoots(unittest.TestCase):
    """引导期根表：随包在前，外部目录按项目根拼"""

    def test_installed_dir_enters_roots_when_present(self) -> None:
        """外部目录存在才进根表

        - 这条红了说明面板与装库看不到外部插件，或空目录也进了表
        """
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            installed = base / INSTALLED_PLUGINS_NAME

            with patch.object(deps_manifest, "ROOT_DIR", base):
                names = [pkg for _, pkg in deps_manifest.plugins_roots()]
                self.assertEqual(names, [PLUGINS_PKG])

                installed.mkdir(parents=True)
                names = [pkg for _, pkg in deps_manifest.plugins_roots()]

            self.assertEqual(names, [PLUGINS_PKG, INSTALLED_PLUGINS_PKG])

    def test_bundled_row_wins_same_name(self) -> None:
        """两根目录同名时精简清单只留随包那一行

        - 这条红了说明外部同名插件会顶掉随包件的那一行
        """
        with tempfile.TemporaryDirectory() as tmp:
            bundled = Path(tmp) / PLUGINS_PKG
            installed = Path(tmp) / INSTALLED_PLUGINS_NAME
            for root, title in ((bundled, "随包"), (installed, "外部")):
                target = root / "dup" / "plugin.toml"
                target.parent.mkdir(parents=True)
                target.write_text(
                    f'name = "dup"\ntitle = "{title}"\nsummary = "同名"\n',
                    encoding="utf-8",
                )

            _write_dependency(installed, "dup")

            rows = deps_manifest.load_manifests(
                [(bundled, PLUGINS_PKG), (installed, INSTALLED_PLUGINS_PKG)]
            )

            self.assertEqual([row["title"] for row in rows], ["随包"])

    def test_shadowed_row_carries_winner_name(self) -> None:
        """被顶掉的那一份连同赢家的名字一起交出来

        - 面板给这行写「插件名被谁占用」用的就是这个名字
        - 各根目录名字不撞时交空表，面板不多出行
        """
        with tempfile.TemporaryDirectory() as tmp:
            bundled = Path(tmp) / PLUGINS_PKG
            installed = Path(tmp) / INSTALLED_PLUGINS_NAME
            for root, title in ((bundled, "随包"), (installed, "外部")):
                target = root / "dup" / "plugin.toml"
                target.parent.mkdir(parents=True)
                target.write_text(
                    f'name = "dup"\ntitle = "{title}"\nsummary = "同名"\n',
                    encoding="utf-8",
                )

            _write_dependency(installed, "dup")

            losers = deps_manifest.shadowed_manifests(
                [(bundled, PLUGINS_PKG), (installed, INSTALLED_PLUGINS_PKG)]
            )

            self.assertEqual(
                [(row["title"], winner) for row, winner in losers], [("外部", "dup")]
            )

            quiet = Path(tmp) / "single" / "plugin.toml"
            quiet.parent.mkdir(parents=True)
            quiet.write_text('name = "single"\ntitle = "独一份"\n', encoding="utf-8")

            self.assertEqual(
                deps_manifest.shadowed_manifests(
                    [(bundled, PLUGINS_PKG), (quiet, INSTALLED_PLUGINS_PKG)]
                ),
                [],
            )


class TestExternalDependencies(unittest.TestCase):
    """外部插件的库从自家声明的依赖表取"""

    def test_libs_come_from_the_own_declaration(self) -> None:
        """两份读取侧都取依赖表那一条，清单里多写的 deps 不算"""
        with tempfile.TemporaryDirectory() as tmp:
            installed = Path(tmp) / INSTALLED_PLUGINS_NAME
            target = installed / "echo" / "plugin.toml"
            target.parent.mkdir(parents=True)
            target.write_text(_ECHO_MANIFEST, encoding="utf-8")
            _write_dependency(installed, "echo")

            rows = deps_manifest.load_manifests([(installed, INSTALLED_PLUGINS_PKG)])
            picked = _manifest._load_manifests(installed, INSTALLED_PLUGINS_PKG, False)

            self.assertEqual([row["deps"] for row in rows], [("markdown==3.10.2",)])
            self.assertEqual(picked["echo"].deps, ("markdown==3.10.2",))

    def test_missing_own_declaration_is_refused(self) -> None:
        """只有清单、没写自家依赖声明，两份读取侧都整份不放行"""
        with tempfile.TemporaryDirectory() as tmp:
            installed = Path(tmp) / INSTALLED_PLUGINS_NAME
            target = installed / "echo" / "plugin.toml"
            target.parent.mkdir(parents=True)
            target.write_text(_ECHO_MANIFEST, encoding="utf-8")

            self.assertEqual(
                deps_manifest.load_manifests([(installed, INSTALLED_PLUGINS_PKG)]), []
            )
            self.assertEqual(
                _manifest._load_manifests(installed, INSTALLED_PLUGINS_PKG, False), {}
            )

    def test_bundled_needs_no_own_declaration(self) -> None:
        """随包那档的库在根声明里，目录里没有依赖声明照样进表"""
        with tempfile.TemporaryDirectory() as tmp:
            bundled = Path(tmp) / PLUGINS_PKG
            _write(bundled, "help")

            rows = deps_manifest.load_manifests([(bundled, PLUGINS_PKG)])

            self.assertEqual([row["deps"] for row in rows], [()])


if __name__ == "__main__":
    unittest.main()
