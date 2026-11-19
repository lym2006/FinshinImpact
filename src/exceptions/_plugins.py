"""插件异常族

- 定义插件注册与生命周期异常
- 定义插件异常文案表，键为异常类
"""

from finshin_sdk.exceptions import BotError


class PluginsError(BotError):
    """插件异常基类"""


class PluginsMissingError(PluginsError):
    """未注册插件"""

    fatal = True


class PluginEntryError(PluginsError):
    """插件入口类不对

    - 写明是模块里没有子类，还是有多个
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

    - 只交出错类别
    """

    def __init__(self, kind: str) -> None:
        self.kind = kind
        super().__init__()


class PluginImportError(PluginsError):
    """外部插件引了本体内部、界面库或平台框架"""

    def __init__(self, plugin: str, target: str, where: str) -> None:
        self.plugin = plugin
        self.target = target
        self.where = where
        super().__init__()


class PluginRoleError(PluginsError):
    """命令权限声明与守卫不一致"""

    def __init__(self, cmd: str) -> None:
        self.cmd = cmd
        super().__init__()


class PluginManifestError(PluginsError):
    """插件清单的开关声明写错"""

    def __init__(self, plugin: str, flag: str, got: str) -> None:
        self.plugin = plugin
        self.flag = flag
        self.got = got
        super().__init__()


PLUGINS_MAP = {
    PluginEntryError: "插件入口不对：{detail}",
    PluginMissingError: "未找到（检查目录结构）",
    PluginDependencyError: "内部依赖缺失",
    PluginLoadError: "加载失败：{kind}",
    PluginRoleError: "命令权限说明与实际拦截对不上",
    PluginManifestError: "插件 {plugin} 的开关 {flag} 默认值只能写 int/float/str（收到 {got}）",
    PluginImportError: "外部插件 {plugin} 不许引本体内部、界面库或平台框架：{target}（{where}）",
    PluginsMissingError: "一只插件都没装上，程序无法运行",
}
