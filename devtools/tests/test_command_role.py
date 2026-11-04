# devtools/tests/test_command_role.py
"""命令权限声明的单元测试

- 覆盖 plugin.toml 里 role 的解析口径
- 覆盖帮助图描述尾部的权限说明
- 覆盖装配期的清单声明与守卫比对
"""

import importlib
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from core.domain import (  # noqa: E402
    PLUGINS_PKG,
    CommandRole,
    HelpKey,
    PluginRoute,
    PluginSpec,
)
from core.dto import (  # noqa: E402
    HelpCommandDTO,
    HelpSectionDTO,
    PluginManifestDTO,
)
from exceptions import PluginRoleError  # noqa: E402
from plugins._shared.access import require_role  # noqa: E402
from plugins._shared.filters import CommandMatch  # noqa: E402
from plugins.help import _services  # noqa: E402
from utils.plugin import _manifest, _register  # noqa: E402


def _section(raw_command: dict[str, Any]) -> list[dict[str, Any]]:
    """把单条命令包成一段帮助贡献"""
    return [
        {HelpKey.SECTION: "工具", HelpKey.NOTE: "", HelpKey.COMMANDS: [raw_command]}
    ]


def _manifest_of(cmd: str, role: CommandRole) -> PluginManifestDTO:
    """造一份只含单条命令声明的插件清单"""
    command = HelpCommandDTO(cmd=cmd, desc="演示命令", role=role)
    return PluginManifestDTO(
        name="demo",
        title="演示",
        summary="演示",
        help_section=(HelpSectionDTO(commands=(command,)),),
    )


def _routes(name: str, limit: CommandRole | None) -> tuple[PluginRoute, ...]:
    """造一条带命令头的路由，limit 为空即不带守卫"""

    async def handler(raw: object, ctx: object) -> None:
        """占位处理函数"""

    guarded = handler if limit is None else require_role(limit)(handler)
    return (PluginRoute(CommandMatch(name), guarded),)


class TestRoleParse(unittest.TestCase):
    """清单里权限档的解析口径"""

    def test_owner_word_parsed(self) -> None:
        command = _manifest._read_help_sections(
            _section({HelpKey.CMD: "wipe", HelpKey.DESC: "清空", "role": "owner"})
        )[0].commands[0]
        self.assertEqual(command.role, CommandRole.OWNER)

    def test_missing_role_defaults_to_member(self) -> None:
        command = _manifest._read_help_sections(
            _section({HelpKey.CMD: "say", HelpKey.DESC: "说话"})
        )[0].commands[0]
        self.assertEqual(command.role, CommandRole.MEMBER)

    def test_word_out_of_table_drops_the_command(self) -> None:
        sections = _manifest._read_help_sections(
            _section({HelpKey.CMD: "say", HelpKey.DESC: "说话", "role": "boss"})
        )
        self.assertEqual(sections[0].commands, ())


class TestMenuRoleNote(unittest.TestCase):
    """帮助图描述尾部的权限说明"""

    def _desc(self, role: CommandRole) -> str:
        command = HelpCommandDTO(cmd="md", desc="图片输出", role=role)
        manifest = PluginManifestDTO(
            name="demo",
            title="演示",
            summary="演示",
            help_section=(HelpSectionDTO(commands=(command,)),),
        )
        with patch.object(_services, "enabled_manifests", lambda path: [manifest]):
            help_list, specs, _ = _services._build_help_menu()
        self.assertEqual(specs["md"].role, role)
        return help_list["md"]

    def test_owner_note_appended(self) -> None:
        self.assertEqual(self._desc(CommandRole.OWNER), "图片输出（仅主人）")

    def test_admin_note_appended(self) -> None:
        self.assertEqual(self._desc(CommandRole.ADMIN), "图片输出（需授权）")

    def test_member_note_left_out(self) -> None:
        self.assertEqual(self._desc(CommandRole.MEMBER), "图片输出")


class TestRoleCheck(unittest.TestCase):
    """装配期的清单声明与守卫比对"""

    def test_declared_owner_with_owner_guard_passes(self) -> None:
        spec = PluginSpec(routes=_routes("wipe", CommandRole.OWNER))
        _register._check_roles(_manifest_of("wipe", CommandRole.OWNER), spec)

    def test_declared_owner_without_guard_fails(self) -> None:
        spec = PluginSpec(routes=_routes("wipe", None))
        with self.assertRaises(PluginRoleError):
            _register._check_roles(_manifest_of("wipe", CommandRole.OWNER), spec)

    def test_guard_tier_below_declaration_fails(self) -> None:
        spec = PluginSpec(routes=_routes("wipe", CommandRole.ADMIN))
        with self.assertRaises(PluginRoleError):
            _register._check_roles(_manifest_of("wipe", CommandRole.OWNER), spec)

    def test_member_declaration_with_guard_fails(self) -> None:
        spec = PluginSpec(routes=_routes("wipe", CommandRole.ADMIN))
        with self.assertRaises(PluginRoleError):
            _register._check_roles(_manifest_of("wipe", CommandRole.MEMBER), spec)

    def test_undeclared_route_without_guard_passes(self) -> None:
        spec = PluginSpec(routes=_routes("other", None))
        _register._check_roles(_manifest_of("wipe", CommandRole.MEMBER), spec)


class TestBuiltinManifests(unittest.TestCase):
    """随仓三只插件的声明与守卫对得上"""

    def test_builtin_plugins_pass_the_check(self) -> None:
        for manifest in _manifest.enabled_manifests(Path("unused")):
            module = importlib.import_module(f"{PLUGINS_PKG}.{manifest.name}")
            _register._check_roles(manifest, module.spec)


if __name__ == "__main__":
    unittest.main()
