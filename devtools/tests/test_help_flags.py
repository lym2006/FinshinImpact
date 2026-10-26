# devtools/tests/test_help_flags.py
"""插件清单可用输入的单元测试

- 覆盖 help.commands 的 flag 解析
- 覆盖帮助图条目行的命令与开关
- 覆盖单命令帮助文案的可用输入行渲染
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
from core.dto import HelpCommandDTO  # noqa: E402
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

    def test_registered_flags_kept_as_declared(self) -> None:
        spec = self._parse(
            {
                HelpKey.CMD: "md",
                HelpKey.DESC: "图片输出",
                HelpKey.FLAGS: [["-i", "图片输入"], ["-t", "输出速度"]],
            }
        )
        self.assertEqual(spec.flags, (("-i", "图片输入"), ("-t", "输出速度")))

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

    def _entries(
        self, flags: tuple[tuple[str, str], ...]
    ) -> list[tuple[str, str, str]]:
        command = HelpCommandDTO(cmd="md", desc="图片输出", flags=flags)
        section = SimpleNamespace(section="", note="", commands=(command,))
        manifest = SimpleNamespace(help_section=(section,))
        with patch.object(_services, "enabled_manifests", lambda path: [manifest]):
            return _services._build_help_menu()[2]

    def test_flags_follow_command_one_entry_each(self) -> None:
        entries = self._entries((("-i", "图片输入"), ("-t", "输出速度")))
        self.assertEqual(
            entries[-4:],
            [
                ("command", "md", "图片输出"),
                ("flag", "-i", "图片输入"),
                ("flag", "-t", "输出速度"),
                ("section", "未完待续", ""),
            ],
        )

    def test_command_without_flags_adds_no_entry(self) -> None:
        entries = self._entries(())
        self.assertEqual(
            entries[-2:],
            [("command", "md", "图片输出"), ("section", "未完待续", "")],
        )

    def test_spec_registered_for_command(self) -> None:
        flags = (("-i", "图片输入"),)
        command = HelpCommandDTO(cmd="md", desc="图片输出", flags=flags)
        section = SimpleNamespace(section="", note="", commands=(command,))
        manifest = SimpleNamespace(help_section=(section,))
        with patch.object(_services, "enabled_manifests", lambda path: [manifest]):
            help_list, specs, _ = _services._build_help_menu()
        self.assertEqual(help_list["md"], "图片输出")
        self.assertEqual(specs["md"].flags, flags)

    def test_digest_follows_flag_note(self) -> None:
        with patch.object(_services, "_display_order", self._entries((("-i", "甲"),))):
            first = _services._menu_digest()
        with patch.object(_services, "_display_order", self._entries((("-i", "乙"),))):
            second = _services._menu_digest()
        self.assertNotEqual(first, second)


class TestUsageLine(unittest.TestCase):
    """单命令帮助的可用输入行"""

    def setUp(self) -> None:
        help_list = {"md": "图片输出", "history": "显示历史记录"}
        command_specs = {
            "md": HelpCommandDTO(cmd="md", desc="图片输出", flags=(("-i", "图片输入"),))
        }
        for name, value in (
            ("help_list", help_list),
            ("command_specs", command_specs),
        ):
            patcher = patch.object(_services, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_help_flag_leads_and_declared_follow(self) -> None:
        text = _services.resolve_single_help("md")
        self.assertIn("-h", text)
        self.assertLess(text.index("-h"), text.index("-i"))

    def test_flag_note_stays_out_of_usage_line(self) -> None:
        self.assertNotIn("图片输入", _services.resolve_single_help("md"))

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


if __name__ == "__main__":
    unittest.main()
