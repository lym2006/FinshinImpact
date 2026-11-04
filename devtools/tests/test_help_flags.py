# devtools/tests/test_help_flags.py
"""插件清单命令输入的单元测试

- 覆盖 help.commands 的开关与参数解析
- 覆盖带值开关的三段形状与开关名形状
- 覆盖帮助图条目行与插件块之间的空行
- 覆盖单命令帮助的开关行与参数行渲染
- 覆盖用法提示行的命令名打头与清单缺项退路
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from core.domain import HelpKey  # noqa: E402
from core.dto import HelpCommandDTO, HelpFlagDTO  # noqa: E402
from plugins._shared.messages import BotMessage  # noqa: E402
from plugins.help import _services  # noqa: E402
from utils.plugin import _manifest  # noqa: E402


def _section(raw_command: Any) -> list[dict[str, Any]]:
    """把单条命令包成一段帮助贡献"""
    return [
        {HelpKey.SECTION: "工具", HelpKey.NOTE: "", HelpKey.COMMANDS: [raw_command]}
    ]


class TestHelpCommandParse(unittest.TestCase):
    """清单里单命令的解析口径"""

    def _parse(self, raw_command: Any) -> HelpCommandDTO:
        return _manifest._read_help_sections(_section(raw_command))[0].commands[0]

    def test_defaults_when_optional_keys_absent(self) -> None:
        spec = self._parse({HelpKey.CMD: "md", HelpKey.DESC: "图片输出"})
        self.assertEqual(spec.flags, ())
        self.assertEqual(spec.args, "")

    def test_registered_args_kept_as_declared(self) -> None:
        spec = self._parse(
            {
                HelpKey.CMD: "push",
                HelpKey.DESC: "推送消息",
                HelpKey.ARGS: "文件路径",
            }
        )
        self.assertEqual(spec.args, "文件路径")

    def test_non_str_args_skips_command(self) -> None:
        sections = _section(
            {HelpKey.CMD: "push", HelpKey.DESC: "推送消息", HelpKey.ARGS: ["路径"]}
        )
        self.assertEqual(_manifest._read_help_sections(sections)[0].commands, ())

    def test_registered_flags_kept_as_declared(self) -> None:
        spec = self._parse(
            {
                HelpKey.CMD: "md",
                HelpKey.DESC: "图片输出",
                HelpKey.FLAGS: [["-i", "图片输入"], ["-t", "输出速度", "秒数"]],
            }
        )
        self.assertEqual(
            spec.flags,
            (HelpFlagDTO("-i", "图片输入"), HelpFlagDTO("-t", "输出速度", "秒数")),
        )

    def test_flag_without_value_name_keeps_value_empty(self) -> None:
        spec = self._parse(
            {HelpKey.CMD: "md", HelpKey.DESC: "图片输出", HelpKey.FLAGS: [["-i", "图"]]}
        )
        self.assertEqual(spec.flags[0].value, "")

    def test_flag_name_without_dash_skips_command(self) -> None:
        sections = _section(
            {HelpKey.CMD: "md", HelpKey.DESC: "图片输出", HelpKey.FLAGS: [["i", "图"]]}
        )
        self.assertEqual(_manifest._read_help_sections(sections)[0].commands, ())

    def test_flag_item_with_four_parts_skips_command(self) -> None:
        sections = _section(
            {
                HelpKey.CMD: "md",
                HelpKey.DESC: "图片输出",
                HelpKey.FLAGS: [["-i", "图", "值", "多一段"]],
            }
        )
        self.assertEqual(_manifest._read_help_sections(sections)[0].commands, ())

    def test_empty_flags_list_parses_empty(self) -> None:
        spec = self._parse(
            {HelpKey.CMD: "md", HelpKey.DESC: "图片输出", HelpKey.FLAGS: []}
        )
        self.assertEqual(spec.flags, ())

    def test_unlisted_key_skips_command(self) -> None:
        sections = _section({HelpKey.CMD: "md", HelpKey.DESC: "图片输出", "arg": True})
        self.assertEqual(_manifest._read_help_sections(sections)[0].commands, ())

    def test_extra_key_skips_command(self) -> None:
        sections = _section(
            {HelpKey.CMD: "md", HelpKey.DESC: "图片输出", "switch": ["-i"]}
        )
        self.assertEqual(_manifest._read_help_sections(sections)[0].commands, ())

    def test_missing_desc_skips_command(self) -> None:
        sections = _section({HelpKey.CMD: "md"})
        self.assertEqual(_manifest._read_help_sections(sections)[0].commands, ())

    def test_non_list_flags_skips_command(self) -> None:
        sections = _section(
            {HelpKey.CMD: "md", HelpKey.DESC: "图片输出", HelpKey.FLAGS: "-i"}
        )
        self.assertEqual(_manifest._read_help_sections(sections)[0].commands, ())

    def test_bare_flag_token_skips_command(self) -> None:
        sections = _section(
            {HelpKey.CMD: "md", HelpKey.DESC: "图片输出", HelpKey.FLAGS: ["-i"]}
        )
        self.assertEqual(_manifest._read_help_sections(sections)[0].commands, ())

    def test_flag_item_without_note_skips_command(self) -> None:
        sections = _section(
            {HelpKey.CMD: "md", HelpKey.DESC: "图片输出", HelpKey.FLAGS: [["-i"]]}
        )
        self.assertEqual(_manifest._read_help_sections(sections)[0].commands, ())

    def test_flag_item_with_empty_note_skips_command(self) -> None:
        sections = _section(
            {HelpKey.CMD: "md", HelpKey.DESC: "图片输出", HelpKey.FLAGS: [["-i", ""]]}
        )
        self.assertEqual(_manifest._read_help_sections(sections)[0].commands, ())

    def test_non_str_member_skips_command(self) -> None:
        sections = _section(
            {HelpKey.CMD: "md", HelpKey.DESC: "图片输出", HelpKey.FLAGS: [12]}
        )
        self.assertEqual(_manifest._read_help_sections(sections)[0].commands, ())


class TestMenuEntries(unittest.TestCase):
    """帮助图的命令条目与开关条目"""

    def _entries(self, flags: tuple[HelpFlagDTO, ...]) -> list[tuple[str, str, str]]:
        command = HelpCommandDTO(cmd="md", desc="图片输出", flags=flags)
        section = SimpleNamespace(section="", note="", commands=(command,))
        manifest = SimpleNamespace(help_section=(section,))
        with patch.object(_services, "enabled_manifests", lambda path: [manifest]):
            return _services._build_help_menu()[2]

    def test_flags_follow_command_one_entry_each(self) -> None:
        entries = self._entries(
            (HelpFlagDTO("-i", "图片输入"), HelpFlagDTO("-t", "输出速度", "秒数"))
        )
        self.assertEqual(
            entries[-5:],
            [
                ("command", "md", "图片输出"),
                ("flag", "-i", "图片输入"),
                ("flag", "-t 秒数", "输出速度"),
                ("gap", "", ""),
                ("section", "未完待续", ""),
            ],
        )

    def test_command_without_flags_adds_no_entry(self) -> None:
        entries = self._entries(())
        self.assertEqual(
            entries[-3:],
            [
                ("command", "md", "图片输出"),
                ("gap", "", ""),
                ("section", "未完待续", ""),
            ],
        )

    def test_blank_row_leads_each_plugin_block(self) -> None:
        entries = self._entries(())
        self.assertEqual(entries[2], ("gap", "", ""))
        self.assertEqual(entries[3][0], "command")

    def test_empty_manifest_adds_no_extra_blank_row(self) -> None:
        manifest = SimpleNamespace(help_section=())
        with patch.object(_services, "enabled_manifests", lambda path: [manifest]):
            entries = _services._build_help_menu()[2]
        self.assertEqual(entries.count(("gap", "", "")), 1)

    def test_spec_registered_for_command(self) -> None:
        flags = (HelpFlagDTO("-i", "图片输入"),)
        command = HelpCommandDTO(cmd="md", desc="图片输出", flags=flags)
        section = SimpleNamespace(section="", note="", commands=(command,))
        manifest = SimpleNamespace(help_section=(section,))
        with patch.object(_services, "enabled_manifests", lambda path: [manifest]):
            help_list, specs, _ = _services._build_help_menu()
        self.assertEqual(help_list["md"], "图片输出")
        self.assertEqual(specs["md"].flags, flags)

    def test_digest_follows_flag_note(self) -> None:
        with patch.object(
            _services, "_display_order", self._entries((HelpFlagDTO("-i", "甲"),))
        ):
            first = _services._menu_digest()
        with patch.object(
            _services, "_display_order", self._entries((HelpFlagDTO("-i", "乙"),))
        ):
            second = _services._menu_digest()
        self.assertNotEqual(first, second)

    def test_digest_follows_flag_value_name(self) -> None:
        with patch.object(
            _services, "_display_order", self._entries((HelpFlagDTO("-t", "甲"),))
        ):
            first = _services._menu_digest()
        with patch.object(
            _services,
            "_display_order",
            self._entries((HelpFlagDTO("-t", "甲", "秒数"),)),
        ):
            second = _services._menu_digest()
        self.assertNotEqual(first, second)

    def test_digest_follows_line_spacing(self) -> None:
        first = _services._menu_digest()
        with patch.object(_services._HELP, "line_spacing", 26):
            second = _services._menu_digest()
        self.assertNotEqual(first, second)


class _SpecStubMixin(unittest.TestCase):
    """按固定清单挂上 help_list 与 command_specs"""

    def setUp(self) -> None:
        help_list = {
            "md": "图片输出",
            "push": "推送消息",
            "convert": "格式转换",
            "history": "显示历史记录",
        }
        command_specs = {
            "md": HelpCommandDTO(
                cmd="md", desc="图片输出", flags=(HelpFlagDTO("-i", "图片输入"),)
            ),
            "push": HelpCommandDTO(cmd="push", desc="推送消息", args="文件路径"),
            "convert": HelpCommandDTO(
                cmd="convert",
                desc="格式转换",
                flags=(HelpFlagDTO("-t", "输出速度", "秒数"),),
            ),
        }
        for name, value in (
            ("help_list", help_list),
            ("command_specs", command_specs),
        ):
            patcher = patch.object(_services, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)


class TestUsageLine(_SpecStubMixin):
    """单命令帮助的开关行与参数行"""

    def test_help_flag_leads_and_declared_follow(self) -> None:
        text = _services.resolve_single_help("md")
        self.assertIn("-h", text)
        self.assertLess(text.index("-h"), text.index("-i"))

    def test_flag_note_stays_out_of_usage_line(self) -> None:
        self.assertNotIn("图片输入", _services.resolve_single_help("md"))

    def test_declared_args_get_own_line(self) -> None:
        self.assertEqual(
            _services.resolve_single_help("push"),
            "推送消息\n可用开关：-h\n可用参数：文件路径",
        )

    def test_value_flag_shows_value_name(self) -> None:
        self.assertEqual(
            _services.resolve_single_help("convert"),
            "格式转换\n可用开关：-h、-t 秒数",
        )

    def test_undeclared_args_leave_no_line(self) -> None:
        self.assertNotIn("可用参数", _services.resolve_single_help("md"))

    def test_command_without_spec_shows_desc_only(self) -> None:
        self.assertEqual(
            _services.resolve_single_help("history"),
            "显示历史记录",
        )

    def test_unknown_name_is_format_error(self) -> None:
        self.assertEqual(
            _services.resolve_single_help("nope"),
            BotMessage.CMD_FORMAT_ERROR,
        )


class TestUsageHint(_SpecStubMixin):
    """多余输入回执的用法提示"""

    def test_hint_leads_with_command_name(self) -> None:
        self.assertEqual(
            _services.resolve_usage_hint("convert"),
            "/convert 用法错误\n可用开关：-h、-t 秒数",
        )

    def test_hint_shows_declared_args(self) -> None:
        self.assertEqual(
            _services.resolve_usage_hint("push"),
            "/push 用法错误\n可用开关：-h\n可用参数：文件路径",
        )

    def test_hint_without_spec_is_format_error(self) -> None:
        self.assertEqual(
            _services.resolve_usage_hint("history"),
            BotMessage.CMD_FORMAT_ERROR,
        )


if __name__ == "__main__":
    unittest.main()
