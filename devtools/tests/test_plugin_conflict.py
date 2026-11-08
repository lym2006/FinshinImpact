# devtools/tests/test_plugin_conflict.py
"""插件抢命令名判定的单元测试

- 在场即随包表恒在场或已勾选，只有在场的插件拿走命令名
- 插件任一命令名被拿走即整只不放行
- 同一命令名多只表外插件同时在场整组作废且不记冲突
- 装载序列与面板勾选集共用 resolve_claims 这一份判定
- 精简清单取到的命令名与注册表认到的同集合
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
    PLUGINS_PKG,
    CommandTaken,
    HelpKey,
    ManifestKey,
    PluginClaim,
    resolve_claims,
)
from services.env_setup import deps_manifest  # noqa: E402
from utils.plugin import _manifest  # noqa: E402

_HEAD = 'name = "{name}"\ntitle = "{name}"\nsummary = "命令名抢占用例"\ndeps = []\n'
_COMMAND = '\n[[help.commands]]\ncmd = "{cmd}"\ndesc = "回一声"\n'


def _write(root: Path, name: str, cmds: tuple[str, ...]) -> None:
    """在目录下造一份声明命令名的清单"""
    target = root / name / "plugin.toml"
    target.parent.mkdir(parents=True)
    text = _HEAD.format(name=name)
    text += '\n[[help]]\nsection = "样例"\n'
    for cmd in cmds:
        text += _COMMAND.format(cmd=cmd)
    target.write_text(text, encoding="utf-8")


def _claim(name: str, *cmds: str) -> PluginClaim:
    """造一条判定入参"""
    return PluginClaim(name=name, commands=cmds)


class TestClaimPolicy(unittest.TestCase):
    """判定本身：谁拿走、谁作废、谁记冲突"""

    def test_single_present_keeps_own_commands(self) -> None:
        """命令名没人抢时自己拿走，也不记冲突"""
        allowed, conflicts = resolve_claims(
            [_claim("extra", "ping")], frozenset({"extra"})
        )

        self.assertEqual(allowed, frozenset({"extra"}))
        self.assertEqual(conflicts, {})

    def test_bundled_present_takes_command_from_external(self) -> None:
        """随包件在场即拿走同名命令，表外件整只不放行并记下被谁拿走"""
        allowed, conflicts = resolve_claims(
            [_claim("help", "history"), _claim("extra", "history")],
            frozenset({"extra"}),
        )

        self.assertEqual(allowed, frozenset({"help"}))
        self.assertEqual(conflicts, {"extra": (CommandTaken("history", "help"),)})

    def test_two_externals_present_together_void_group(self) -> None:
        """同一命令名两只表外插件同时在场整组作废且不记冲突

        - 这条挡的是用户手改状态文件把互斥的两只一起勾上
        """
        allowed, conflicts = resolve_claims(
            [_claim("first", "ping"), _claim("second", "ping")],
            frozenset({"first", "second"}),
        )

        self.assertEqual(allowed, frozenset())
        self.assertEqual(conflicts, {})

    def test_absent_external_marked_conflict(self) -> None:
        """不在场但命令名已被拿走的照记冲突，面板据此禁掉勾选"""
        allowed, conflicts = resolve_claims(
            [_claim("first", "ping"), _claim("later", "ping")], frozenset({"first"})
        )

        self.assertEqual(allowed, frozenset({"first"}))
        self.assertEqual(conflicts, {"later": (CommandTaken("ping", "first"),)})

    def test_bundled_internal_clash_not_marked(self) -> None:
        """随包表内两只抢同一个命令名属本体自己的账，两只都放行也不记冲突"""
        allowed, conflicts = resolve_claims(
            [_claim("help", "clear"), _claim("grant", "clear")], None
        )

        self.assertEqual(allowed, frozenset({"help", "grant"}))
        self.assertEqual(conflicts, {})

    def test_one_taken_command_voids_whole_plugin(self) -> None:
        """多条命令里只有一条被拿走，整只也不放行"""
        allowed, conflicts = resolve_claims(
            [_claim("help", "history"), _claim("extra", "ping", "history")],
            frozenset({"extra"}),
        )

        self.assertNotIn("extra", allowed)
        self.assertEqual(conflicts, {"extra": (CommandTaken("history", "help"),)})


class TestLoaderRefusal(unittest.TestCase):
    """装载序列：判定挡住的插件不进序列"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        _write(self.root, "help", ("history",))
        _write(self.root, "first", ("ping",))
        _write(self.root, "second", ("ping",))
        patcher = patch.object(
            _manifest, "_plugins_roots", lambda: [(self.root, PLUGINS_PKG)]
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.state = self.root / "plugins.toml"

    def _picked(self) -> list[str]:
        """取本次装载序列的插件名"""
        return [m.name for m in _manifest.enabled_manifests(self.state)]

    def test_clashing_pair_neither_loads(self) -> None:
        """状态文件同时勾上互斥的两只，两只都不装载"""
        self.state.write_text('enabled = ["first", "second"]\n', encoding="utf-8")

        self.assertEqual(self._picked(), ["help"])

    def test_single_side_loads(self) -> None:
        """只勾其中一只即正常装载"""
        self.state.write_text('enabled = ["first"]\n', encoding="utf-8")

        self.assertEqual(self._picked(), ["help", "first"])

    def test_bundled_command_beats_external(self) -> None:
        """表外插件声明了随包件已拿走的命令名，勾上也不装载"""
        _write(self.root, "shadow", ("history",))
        self.state.write_text('enabled = ["shadow"]\n', encoding="utf-8")

        self.assertEqual(self._picked(), ["help"])


class TestTwoReadersAgree(unittest.TestCase):
    """命令名集合：面板读的精简清单与注册表读的清单同集合"""

    def _rows_and_manifests(
        self, root: Path
    ) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
        """分别取两份读侧认到的命令名"""
        rows = {
            row[ManifestKey.NAME]: tuple(cmd for cmd, _ in row[HelpKey.COMMANDS])
            for row in deps_manifest.load_manifests([root])
        }
        manifests = {
            name: tuple(
                command.cmd
                for section in manifest.help_section
                for command in section.commands
            )
            for name, manifest in _manifest._load_manifests(root, PLUGINS_PKG).items()
        }
        return rows, manifests

    def test_same_commands_on_good_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "help", ("history", "clear"))
            _write(root, "extra", ())

            rows, manifests = self._rows_and_manifests(root)

            self.assertEqual(rows, manifests)
            self.assertEqual(rows["help"], ("history", "clear"))

    def test_both_skip_command_missing_desc(self) -> None:
        """缺说明的那条命令名两边都不认，判定不会只在一侧成立"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "help", ("history",))
            target = root / "help" / "plugin.toml"
            target.write_text(
                target.read_text(encoding="utf-8")
                + '\n[[help.commands]]\ncmd = "half"\nflags = []\n',
                encoding="utf-8",
            )

            rows, manifests = self._rows_and_manifests(root)

            self.assertEqual(rows, manifests)
            self.assertEqual(rows["help"], ("history",))


if __name__ == "__main__":
    unittest.main()
