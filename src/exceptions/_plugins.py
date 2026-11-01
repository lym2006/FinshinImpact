# src/exceptions/_plugins.py
"""插件异常族

- 定义插件注册与生命周期异常
- 注册失败的定性文案按异常类收进 PLUGINS_MAP，异常本体走调试日志
"""

from ._base import BotError


class PluginsError(BotError):
    """插件异常基类"""


class PluginsMissingError(PluginsError):
    """未注册插件"""

    fatal = True  # 环境缺失非配置可修，向导无从补救


class PluginSpecError(PluginsError):
    """插件没交 spec"""


class PluginMissingError(PluginsError):
    """插件模块本身不存在"""


class PluginDependencyError(PluginsError):
    """插件内部依赖缺失"""


class PluginLoadError(PluginsError):
    """插件加载抛错

    - kind 取异常类名，面板只报到哪一类
    """

    def __init__(self, kind: str) -> None:
        self.kind = kind
        super().__init__()


class AIError(PluginsError):
    """AI 插件异常基类"""


PLUGINS_MAP = {
    PluginSpecError: "缺少 spec 属性（检查 __init__.py）",
    PluginMissingError: "未找到（检查目录结构）",
    PluginDependencyError: "内部依赖缺失",
    PluginLoadError: "加载失败：{kind}",
}
