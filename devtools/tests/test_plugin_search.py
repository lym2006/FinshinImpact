# devtools/tests/test_plugin_search.py
"""面板搜索件与命令明细的单元测试

- 名字一列比的是面板上看得见的显示名，没填标题即目录名
- 命令名带斜杠与不带斜杠都算命中，比的是子串包含
- 输入串先转小写再比，大小写不影响命中
- 筛选档决定比哪一列，只搜名字不认命令名，只搜命令不认名字
- 搜索只切每行显隐，行上挂的那件跟着行一起隐
- 一只都没命中时顶一句提示，输入串清空即整表恢复显示
- 命令明细逐条写成一行，一条都没声明只交一句说明
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from core.domain import HelpKey, ManifestKey  # noqa: E402
from skin.messages import PluginMessage  # noqa: E402
from ui._guide._conflict import _command_lines  # noqa: E402
from ui._guide._search import (  # noqa: E402
    _SCOPE_ALL,
    _SCOPE_CMD,
    _SCOPE_NAME,
    ROLE_MANIFEST,
    _matches,
    _PluginSearch,
)


def _manifest(title: str, cmds: tuple[tuple[str, str], ...]) -> dict[str, object]:
    """造一份搜索与明细要读的三列最小清单"""
    return {
        ManifestKey.NAME: "ping_a",
        ManifestKey.TITLE: title,
        HelpKey.COMMANDS: cmds,
    }


class TestMatchScope(unittest.TestCase):
    """命中判定：比哪一列、命令名带不带斜杠"""

    def test_display_name_beats_dir_name(self) -> None:
        """显示名命中即留，目录名压根不比"""
        manifest = _manifest("撞名 1", (("ping", "回一声"),))

        self.assertTrue(_matches(manifest, "撞名 1", _SCOPE_ALL))
        self.assertFalse(_matches(manifest, "ping_a", _SCOPE_ALL))

    def test_blank_title_falls_back_to_dir_name(self) -> None:
        """没填标题时显示名就是目录名"""
        manifest = _manifest("", (("ping", "回一声"),))

        self.assertTrue(_matches(manifest, "ping_a", _SCOPE_NAME))

    def test_command_hits_with_and_without_slash(self) -> None:
        """命令名带不带斜杠都算命中"""
        manifest = _manifest("撞名 1", (("Ping", "回一声"),))

        for query in ("ping", "/ping", "pin", "/pi"):
            with self.subTest(query=query):
                self.assertTrue(_matches(manifest, query, _SCOPE_ALL))

    def test_scope_picks_the_column_compared(self) -> None:
        """档位限定列：只搜名字不认命令名，只搜命令不认名字"""
        manifest = _manifest("撞名 1", (("ping", "回一声"),))

        self.assertTrue(_matches(manifest, "撞名", _SCOPE_NAME))
        self.assertFalse(_matches(manifest, "ping", _SCOPE_NAME))
        self.assertTrue(_matches(manifest, "ping", _SCOPE_CMD))
        self.assertFalse(_matches(manifest, "撞名", _SCOPE_CMD))

    def test_command_desc_is_not_a_hit_criterion(self) -> None:
        """明细里那句说明不参与搜索，命中的只有命令名"""
        manifest = _manifest("撞名 1", (("ping", "回一声"),))

        self.assertFalse(_matches(manifest, "回一声", _SCOPE_ALL))


class TestCommandLines(unittest.TestCase):
    """行尾看命令的明细文案"""

    def test_one_line_per_command(self) -> None:
        """每条命令写成一行，命令名与说明同现"""
        manifest = _manifest("撞名 1", (("ping", "回一声"), ("pong", "回两声")))

        self.assertEqual(
            _command_lines(manifest),
            [
                PluginMessage.COMMAND_LINE.format(cmd="ping", desc="回一声"),
                PluginMessage.COMMAND_LINE.format(cmd="pong", desc="回两声"),
            ],
        )

    def test_no_declaration_yields_one_note(self) -> None:
        """一条都没声明时只交一句说明，明细窗不至于空着"""
        manifest = _manifest("撞名 1", ())

        self.assertEqual(_command_lines(manifest), [PluginMessage.COMMAND_NONE])


class TestRowVisibility(unittest.TestCase):
    """显隐成对与零命中提示"""

    def setUp(self) -> None:
        self.items = [MagicMock(), MagicMock(), MagicMock()]
        self.widgets = {item: MagicMock() for item in self.items}
        for index, manifest in enumerate(
            (
                _manifest("撞名 1", (("ping", "回一声"),)),
                _manifest("撞名 2", (("pong", "回两声"),)),
                _manifest("撞名 3", ()),
            )
        ):
            self.items[index].data.return_value = manifest
        self.tip = MagicMock()

    def _refresh(self, query: str, scope: str = _SCOPE_ALL) -> None:
        """用假件跑一次刷新，清单与输入都换成替身"""
        rows = SimpleNamespace(
            count=lambda: len(self.items),
            item=lambda index: self.items[index],
            itemWidget=self.widgets.__getitem__,
        )
        search = SimpleNamespace(
            _edit=MagicMock(**{"text.return_value": query}),
            _scope=MagicMock(**{"currentData.return_value": scope}),
            _rows=rows,
            _tip=self.tip,
        )
        _PluginSearch.refresh(search)

    def test_blank_query_restores_every_row(self) -> None:
        """清空输入即整表恢复显示"""
        self._refresh("")

        for item in self.items:
            item.setHidden.assert_called_once_with(False)
            self.widgets[item].setHidden.assert_called_once_with(False)
        self.tip.setVisible.assert_called_once_with(False)

    def test_widget_hides_with_its_row(self) -> None:
        """不匹配的行隐掉，行上挂的那件跟着隐"""
        self._refresh("pong")

        self.items[0].setHidden.assert_called_once_with(True)
        self.widgets[self.items[0]].setHidden.assert_called_once_with(True)
        self.items[1].setHidden.assert_called_once_with(False)
        self.widgets[self.items[1]].setHidden.assert_called_once_with(False)

    def test_query_is_trimmed_and_folded(self) -> None:
        """输入串去掉首尾空格再转小写，大写照样命中"""
        self._refresh("  PONG  ")

        self.items[1].setHidden.assert_called_once_with(False)

    def test_zero_hit_raises_tip(self) -> None:
        """一只都没命中时在清单下方顶一句提示"""
        self._refresh("nobody")

        self.tip.setVisible.assert_called_once_with(True)

    def test_rows_are_read_through_manifest_role(self) -> None:
        """筛选读的是行上那份最小清单，角色取错就整表隐掉"""
        self._refresh("ping")

        for item in self.items:
            item.data.assert_called_once_with(ROLE_MANIFEST)


if __name__ == "__main__":
    unittest.main()
