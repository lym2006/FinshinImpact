# src/core/dto/_plugin.py
"""插件数据传输对象

- 定义插件自描述清单与帮助菜单贡献
- 字段与 plugin.toml 对应
"""

from dataclasses import dataclass

from ..domain import CommandRole


@dataclass(frozen=True, slots=True)
class HelpFlagDTO:
    """帮助菜单的单只开关

    - 与 plugin.toml 的 flags 每项同构，前两段是「开关 说明」
    - value 是第三段写的值名，非空即这只开关要带值
    """

    name: str
    desc: str
    value: str = ""


@dataclass(frozen=True, slots=True)
class HelpCommandDTO:
    """帮助菜单单命令

    - 与 plugin.toml 的 [[help.commands]] 同构
    - flags 每项是一只开关，顺序即帮助图上的列出顺序
    - -h 全命令默认可用，不必登记
    - args 是命令后面要带的内容，空即不收
    - role 缺省为用户档，即谁都能使
    """

    cmd: str
    desc: str
    flags: tuple[HelpFlagDTO, ...] = ()
    args: str = ""
    role: CommandRole = CommandRole.MEMBER


@dataclass(frozen=True, slots=True)
class HelpSectionDTO:
    """帮助菜单贡献段

    - section 为空不进标题行
    - note 为空省略备注行
    """

    section: str = ""
    note: str = ""
    commands: tuple[HelpCommandDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class PluginManifestDTO:
    """插件自描述清单

    - deps 只写顶层依赖的 pin 版本串，不含传递依赖
    - assets 值为「模块名 资源名」两段
    - 目录摘要不含 summary，描述改动不触发弹面板
    """

    name: str
    title: str
    summary: str
    deps: tuple[str, ...] = ()
    assets: tuple[str, ...] = ()
    help_section: tuple[HelpSectionDTO, ...] = ()
