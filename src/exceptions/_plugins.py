# src/exceptions/_plugins.py
"""插件异常族

- 定义插件注册与生命周期异常
- 注册失败的定性文案按异常类收进同文件文案表，异常本体走调试日志
"""

from ._base import BotError


class PluginsError(BotError):
    """插件异常基类"""


class PluginsMissingError(PluginsError):
    """未注册插件"""

    fatal = True  # 环境缺失非配置可修，向导无从补救


class PluginEntryError(PluginsError):
    """插件入口类不对

    - 判因写明是模块里没有子类，还是不止一只
    """

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__()


class PluginMissingError(PluginsError):
    """插件模块本身不存在"""


class PluginDependencyError(PluginsError):
    """插件内部依赖缺失"""


class PluginLoadError(PluginsError):
    """插件加载抛错

    - 异常类名随异常携带，面板只报到哪一类
    """

    def __init__(self, kind: str) -> None:
        self.kind = kind
        super().__init__()


class PluginImportError(PluginsError):
    """外部插件引了本体内部

    - 被引用的内部模块名随异常携带
    - 出处落在哪份文件哪一行随异常携带
    """

    def __init__(self, plugin: str, target: str, where: str) -> None:
        self.plugin = plugin
        self.target = target
        self.where = where
        super().__init__()


class PluginRoleError(PluginsError):
    """命令权限声明与守卫不一致

    - 对不上的命令名随异常携带，本体走调试日志
    """

    def __init__(self, cmd: str) -> None:
        self.cmd = cmd
        super().__init__()


PLUGINS_MAP = {
    PluginEntryError: "插件入口不对：{detail}",
    PluginMissingError: "未找到（检查目录结构）",
    PluginDependencyError: "内部依赖缺失",
    PluginLoadError: "加载失败：{kind}",
    PluginRoleError: "命令权限说明与实际拦截对不上",
    PluginImportError: "外部插件 {plugin} 不许引本体内部：{target}（{where}）",
    PluginsMissingError: "一只插件都没装上，程序无法运行",
}
