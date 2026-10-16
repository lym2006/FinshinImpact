# src/core/domain/_plugin.py
"""插件对象

- 定义插件加载优先级词表
- 定义插件相关文件名词表
- 定义插件数据契约的键名词表
"""

from enum import IntEnum, StrEnum

PLUGINS_PKG = "plugins"  # 插件树顶层包名，find_spec 与动态导入路径共用同值


class CommandPriority(IntEnum):
    """插件加载优先级

    - 数值越小越优先，同值按 name 字典序
    - 新插件一律取 NORMAL，禁止在现有档位之间插值
    """

    FIRST = 0  # help 独占
    NORMAL = 10  # 常规与新增默认
    LAST = 50  # AI 独占


class PluginFile(StrEnum):
    """插件相关文件名

    - 文件名单源，禁止在别处重复定义
    """

    MANIFEST = "plugin.toml"  # 位于各插件目录，存插件自描述清单
    STATE = "plugins.toml"  # 位于实例目录，存启用集与 catalog 指纹


class ManifestKey(StrEnum):
    """插件清单键名

    - 与 plugin.toml 字段一一对应
    """

    NAME = "name"
    TITLE = "title"
    SUMMARY = "summary"
    CORE = "core"
    ORDER = "order"
    DEPS = "deps"
    ASSETS = "assets"
    HELP = "help"


class HelpKey(StrEnum):
    """帮助贡献键名

    - 段级与命令级共用
    """

    SECTION = "section"
    NOTE = "note"
    COMMANDS = "commands"
    CMD = "cmd"
    DESC = "desc"
    FLAGS = "flags"


class StateKey(StrEnum):
    """实例状态文件键名

    - 面板写侧与运行期读侧共用
    """

    ENABLED = "enabled"
    CATALOG = "catalog"
