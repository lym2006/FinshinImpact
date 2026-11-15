"""适配器异常族

- 定义平台装配件缺失、版本不合与被拒装的异常
"""

from finshin_sdk.exceptions import BotError


class AdapterError(BotError):
    """适配器异常基类"""


class AdapterMissingError(AdapterError):
    """平台适配器未安装

    - 平台标识随异常携带，面板那句从这里取
    """

    fatal = True  # 出路是装件，向导改配置修不了这个

    def __init__(self, platform: str) -> None:
        self.platform = platform
        super().__init__()


class AdapterOutOfDateError(AdapterError):
    """适配器要的接口版本比本机新

    - 清单写的版本下限随异常携带
    - 本机接口包的版本号随异常携带
    """

    fatal = True  # 出路是更新适配器，向导改配置修不了这个

    def __init__(self, platform: str, requires: str, sdk: str) -> None:
        self.platform = platform
        self.requires = requires
        self.sdk = sdk
        super().__init__()


class AdapterImportError(AdapterError):
    """外部适配器引了本体内部

    - 平台标识、被引用的内部模块名与出处随异常携带
    """

    fatal = True  # 出路是换一只守规矩的适配器，向导改配置修不了这个

    def __init__(self, platform: str, target: str, where: str) -> None:
        self.platform = platform
        self.target = target
        self.where = where
        super().__init__()


ADAPTER_MAP = {
    AdapterMissingError: "这个平台的适配器还没装：{platform}",
    AdapterOutOfDateError: "这个平台的适配器要接口包 {requires} 以上，本机是 {sdk}",
    AdapterImportError: "这个平台的适配器不许引本体内部：{platform}（{target}，{where}）",
}
