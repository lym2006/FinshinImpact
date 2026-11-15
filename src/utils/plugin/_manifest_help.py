"""插件清单帮助贡献解析

- 解析清单里的帮助段与段内单条命令
"""

from exceptions import PluginManifestError
from finshin_sdk.domain import ArgsValue, CommandRole, HelpKey, is_flag_name
from finshin_sdk.dto import HelpCommandDTO, HelpFlagDTO, HelpSectionDTO

from ..logger import get_logger

_logger = get_logger("Plugin")

# 帮助贡献键名白名单
_HELP_SECTION_KEYS = frozenset({HelpKey.SECTION, HelpKey.NOTE, HelpKey.COMMANDS})
_HELP_COMMAND_KEYS = frozenset({HelpKey.CMD, HelpKey.DESC})
_HELP_COMMAND_ALLOWED = _HELP_COMMAND_KEYS | frozenset(
    {HelpKey.FLAGS, HelpKey.ARGS, HelpKey.ROLE}
)

# 清单权限档词表，只认这三个词
_ROLE_WORDS: dict[str, CommandRole] = {
    "owner": CommandRole.OWNER,
    "admin": CommandRole.ADMIN,
    "member": CommandRole.MEMBER,
}

# 清单开关项的段数：两段是「开关 说明」，第三段是带值开关的值名
_FLAG_ITEM_MIN_LEN = 2
_FLAG_ITEM_MAX_LEN = 3


def read_help_sections(
    raw_sections: object,
    plugin_name: str,
) -> tuple[HelpSectionDTO, ...]:
    """解析帮助贡献段列表

    - 非列表入参视为无贡献
    - 段缺必填或必填类型不符时整段跳过
    - 单条命令形状错时该条跳过
    - 段与命令里多写的键忽略并记调试日志
    """
    if not isinstance(raw_sections, list):
        return ()

    sections: list[HelpSectionDTO] = []
    for raw_section in raw_sections:
        if not isinstance(raw_section, dict):
            continue

        section = raw_section.get(HelpKey.SECTION, "")
        note = raw_section.get(HelpKey.NOTE, "")
        raw_commands = raw_section.get(HelpKey.COMMANDS, [])
        if not isinstance(section, str) or not isinstance(note, str):
            continue
        if not isinstance(raw_commands, list):
            continue

        unknown = sorted(set(raw_section) - _HELP_SECTION_KEYS)
        if unknown:
            _logger.debug(
                f"插件 {plugin_name} 的帮助段 {section} 忽略未知键 {'、'.join(unknown)}"
            )

        commands = tuple(
            command
            for command in (
                _parse_help_command(raw_command, plugin_name, section)
                for raw_command in raw_commands
            )
            if command is not None
        )
        sections.append(HelpSectionDTO(section=section, note=note, commands=commands))

    return tuple(sections)


def _parse_help_command(
    raw: object,
    plugin_name: str,
    section: str,
) -> HelpCommandDTO | None:
    """解析单条命令贡献

    - 缺必填或必填类型不符时返回 None
    - flags 可缺省，缺省为空元组
    - 开关项的段数与前两段形状不合即整条拒收
    - 默认值写成三种类型以外即当场报错，不在这里静默吞
    - args 可缺省，缺省即命令后面不带内容
    - role 可缺省，缺省即用户档，词表外的值整条拒收
    - 多写的键忽略并记调试日志
    """
    if not isinstance(raw, dict):
        return None
    if not _HELP_COMMAND_KEYS.issubset(raw):
        return None
    if not all(isinstance(raw[key], str) for key in _HELP_COMMAND_KEYS):
        return None

    unknown = sorted(set(raw) - _HELP_COMMAND_ALLOWED)
    if unknown:
        _logger.debug(
            f"插件 {plugin_name} 帮助段 {section} 的 {raw[HelpKey.CMD]} 忽略未知键 {'、'.join(unknown)}"
        )

    raw_flags = raw.get(HelpKey.FLAGS, [])
    if not isinstance(raw_flags, list):
        return None
    flags: list[HelpFlagDTO] = []
    for raw_flag in raw_flags:
        parts = _flag_parts(raw_flag, plugin_name)
        if parts is None:
            return None
        flags.append(HelpFlagDTO(name=parts[0], desc=parts[1], default=parts[2]))

    raw_role = raw.get(HelpKey.ROLE, "")
    if not isinstance(raw_role, str) or (raw_role and raw_role not in _ROLE_WORDS):
        return None

    raw_args = raw.get(HelpKey.ARGS, "")
    if not isinstance(raw_args, str):
        return None

    return HelpCommandDTO(
        cmd=raw[HelpKey.CMD],
        desc=raw[HelpKey.DESC],
        flags=tuple(flags),
        args=raw_args,
        role=_ROLE_WORDS.get(raw_role, CommandRole.MEMBER),
    )


def _checked_default(raw_default: object, plugin_name: str, name: str) -> ArgsValue:
    """核清单写的默认值是哪一种

    - 只认整数、小数、文本三种，其余类型当场报错，报的是类型本名
    - 空文本按没写值处理，同样当场报错
    """
    if isinstance(raw_default, bool):
        raise PluginManifestError(plugin_name, name, "bool")
    if isinstance(raw_default, (int, float)):
        return raw_default
    if isinstance(raw_default, str):
        if not raw_default:
            raise PluginManifestError(plugin_name, name, "空 str")
        return raw_default
    raise PluginManifestError(plugin_name, name, type(raw_default).__name__)


def _flag_parts(
    raw_flag: object, plugin_name: str
) -> tuple[str, str, ArgsValue | None] | None:
    """拆开关项的三段

    - 前两段是「开关 说明」，都须是非空文本
    - 首段按开关名形状校验，与命令解析共用一条规则
    - 第三段是默认值，缺它即纯开关
    - 默认值只认整数、小数、文本三种，写成别的类型即当场报错
    - 段数与前两段形状不合返回 None
    """
    if not isinstance(raw_flag, list):
        return None
    if not _FLAG_ITEM_MIN_LEN <= len(raw_flag) <= _FLAG_ITEM_MAX_LEN:
        return None
    name, desc = raw_flag[0], raw_flag[1]
    if not isinstance(name, str) or not is_flag_name(name):
        return None
    if not isinstance(desc, str) or not desc:
        return None
    if len(raw_flag) == _FLAG_ITEM_MIN_LEN:
        return name, desc, None

    return name, desc, _checked_default(raw_flag[_FLAG_ITEM_MIN_LEN], plugin_name, name)
