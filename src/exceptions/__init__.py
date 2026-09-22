# src/exceptions/__init__.py
"""异常聚合包

- 定义全部自定义异常族与文案模板
"""

from ._base import BotError
from ._config import (
    CONFIG_MAP,
    ConfigAttrError,
    ConfigError,
    ConfigInputError,
    ConfigMissingError,
    ConfigOutputError,
    ConfigParseError,
    ConfigPathMissingError,
    ConfigTemplateMissingError,
)
from ._connectivity import (
    CONNECTIVITY_MAP,
    ConnectivityError,
    DirectTimeoutError,
    ProxyAddressError,
    ProxyConnectionRefusedError,
    ProxyError,
    ProxySchemeError,
    ProxyTimeoutError,
    TelegramServerError,
    TokenError,
)
from ._gui import (
    GUI_MAP,
    DashboardWriteError,
    FontError,
    FontFamilyError,
    FontLoadError,
    FontMissingError,
    FontRegisterError,
    GUIError,
)
from ._initial import (
    INITIAL_MAP,
    InitError,
    LocalVersionError,
    NewVersionError,
    RemoteVersionError,
    VersionError,
)
from ._network import (
    NETWORK_MAP,
    ConnectionFailedError,
    HTTPStatusError,
    NetworkError,
    RequestTimeoutError,
)
from ._plugins import AIError, AITaskStoppedError, PluginsMissingError

MAPS = {
    "GUI": GUI_MAP,
    "Config": CONFIG_MAP,
    "Init": INITIAL_MAP,
    "Network": NETWORK_MAP,
    "Connectivity": CONNECTIVITY_MAP,
}

__all__ = [
    # 异常映射表
    "MAPS",
    # 基类
    "BotError",
    # 初始化
    "InitError",
    "VersionError",
    "NewVersionError",
    "RemoteVersionError",
    "LocalVersionError",
    # 配置系统
    "ConfigError",
    "ConfigMissingError",
    "ConfigTemplateMissingError",
    "ConfigInputError",
    "ConfigOutputError",
    "ConfigParseError",
    "ConfigAttrError",
    "ConfigPathMissingError",
    # 网络与 API
    "NetworkError",
    "HTTPStatusError",
    "RequestTimeoutError",
    "ConnectionFailedError",
    # 连接性
    "ConnectivityError",
    "DirectTimeoutError",
    "TokenError",
    "TelegramServerError",
    "ProxyError",
    "ProxyAddressError",
    "ProxySchemeError",
    "ProxyTimeoutError",
    "ProxyConnectionRefusedError",
    # GUI
    "GUIError",
    "DashboardWriteError",
    "FontError",
    "FontMissingError",
    "FontLoadError",
    "FontRegisterError",
    "FontFamilyError",
    # 插件
    "PluginsMissingError",
    "AIError",
    "AITaskStoppedError",
]
