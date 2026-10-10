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
    ProfileMissingError,
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
from ._network import (
    NETWORK_MAP,
    ConnectionFailedError,
    HTTPStatusError,
    NetworkError,
    RequestTimeoutError,
)
from ._plugins import AIError, AITaskStoppedError, PluginsMissingError
from ._version import (
    VERSION_MAP,
    LocalVersionError,
    NewVersionError,
    RemoteVersionError,
    VersionError,
)

# 异常映射表域键
MAP_KEY_CONNECTIVITY = "Connectivity"
MAP_KEY_PROXY = "Proxy"
MAP_KEY_CONFIG = "Config"
MAP_KEY_NETWORK = "Network"
MAP_KEY_VERSION = "Version"

MAPS = {
    "GUI": GUI_MAP,
    MAP_KEY_CONFIG: CONFIG_MAP,
    MAP_KEY_VERSION: VERSION_MAP,
    MAP_KEY_NETWORK: NETWORK_MAP,
    MAP_KEY_CONNECTIVITY: CONNECTIVITY_MAP,
}

__all__ = [
    # 异常映射表
    "MAPS",
    # 基类
    "BotError",
    # 版本
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
    "ProfileMissingError",
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
