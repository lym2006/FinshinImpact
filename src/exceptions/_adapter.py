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


ADAPTER_MAP = {
    AdapterMissingError: "这个平台的适配器还没装：{platform}",
}
