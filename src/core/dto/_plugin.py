# src/core/dto/_plugin.py
"""插件数据传输对象

- 定义插件自描述清单与帮助菜单贡献
- 字段与 plugin.toml 对应
"""

from dataclasses import dataclass

from ..domain import CommandPriority


@dataclass(frozen=True, slots=True)
class HelpCommandDTO:
    """帮助菜单单命令

    - 与 plugin.toml 的 [[help.commands]] 同构
    """

    cmd: str
    desc: str


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
    - summary 不参与目录摘要计算，描述改动不触发弹面板
    """

    name: str
    title: str
    summary: str
    core: bool = False
    order: CommandPriority = CommandPriority.NORMAL
    deps: tuple[str, ...] = ()
    assets: tuple[str, ...] = ()
    help_section: tuple[HelpSectionDTO, ...] = ()
