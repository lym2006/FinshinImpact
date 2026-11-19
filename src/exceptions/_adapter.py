"""适配器异常族

- 定义适配器安装、版本与引本体内部三类异常
"""

from finshin_sdk.exceptions import BotError


class AdapterError(BotError):
    """适配器异常基类

    - 整族致命等级置真
    """

    fatal = True


class AdapterMissingError(AdapterError):
    """平台适配器未安装"""

    def __init__(self, platform: str) -> None:
        self.platform = platform
        super().__init__()


class AdapterNotInstalledError(AdapterError):
    """适配器包不在环境里"""

    def __init__(self, platform: str, module: str) -> None:
        self.platform = platform
        self.module = module
        super().__init__()


class AdapterOutOfDateError(AdapterError):
    """适配器要的接口版本与本机不符"""

    def __init__(self, platform: str, requires: str, sdk: str) -> None:
        self.platform = platform
        self.requires = requires
        self.sdk = sdk
        super().__init__()


class AdapterImportError(AdapterError):
    """外部适配器导入本体内部模块"""

    def __init__(self, platform: str, target: str, where: str) -> None:
        self.platform = platform
        self.target = target
        self.where = where
        super().__init__()


ADAPTER_MAP = {
    AdapterMissingError: "{platform} 平台的适配器还没装\n装完请重新打开本程序",
    AdapterNotInstalledError: (
        "{platform} 平台的适配器没装进环境：找不到 {module}\n装完请重新打开本程序"
    ),
    AdapterOutOfDateError: (
        "{platform} 平台的适配器要接口包 {requires}，本机接口包是 {sdk}"
    ),
    AdapterImportError: "{platform} 平台的适配器不许引本体内部（{target}，{where}）",
}
