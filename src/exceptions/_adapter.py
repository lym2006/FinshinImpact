# src/exceptions/_adapter.py
"""适配器异常族

- 定义平台装配件缺失的异常
"""

from ._base import BotError


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


ADAPTER_MAP = {
    AdapterMissingError: "这个平台的适配器还没装：{platform}",
    AdapterOutOfDateError: "这个平台的适配器要接口包 {requires} 以上，本机是 {sdk}",
}
