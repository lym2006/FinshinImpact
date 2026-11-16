"""适配器异常族

- 定义平台装配件缺失、版本不合与被拒装的异常
"""

from finshin_sdk.exceptions import BotError


class AdapterError(BotError):
    """适配器异常基类

    - 致命等级整族置真：出路在装件、更新或换件，改配置修不好
    """

    fatal = True


class AdapterMissingError(AdapterError):
    """平台适配器未安装"""

    def __init__(self, platform: str) -> None:
        self.platform = platform
        super().__init__()


class AdapterNotInstalledError(AdapterError):
    """适配器声明在场，环境里取不到那只包"""

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
    """外部适配器引了本体内部"""

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
