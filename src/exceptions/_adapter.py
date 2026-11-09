# src/exceptions/_adapter.py
"""适配器异常族

- 定义平台装配件缺失的异常
"""

from ._base import BotError


class AdapterError(BotError):
    """适配器异常基类"""


class AdapterMissingError(AdapterError):
    """平台适配器未安装

    - platform 取平台标识，面板那句取它
    """

    fatal = True  # 出路是装件，向导改配置修不了这个

    def __init__(self, platform: str) -> None:
        self.platform = platform
        super().__init__()


class AdapterOutOfDateError(AdapterError):
    """适配器要的接口版本比本机新

    - requires 取清单写的下限，sdk 取本机接口包的版本
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
