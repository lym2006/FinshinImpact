# src/exceptions/__init__.py
"""异常聚合包

- 代发全部自定义异常族
- 代发取异常那句人话的那只手
"""

from ._adapter import (
    AdapterError,
    AdapterMissingError,
    AdapterOutOfDateError,
)
from ._base import BotError
from ._config import (
    ConfigAttrError,
    ConfigError,
    ConfigInputError,
    ConfigMissingError,
    ConfigOutputError,
    ConfigPathMissingError,
    ProfileMissingError,
)
from ._connectivity import (
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
from ._describe import describe_error
from ._domain import DomainError, MessageVanishedError
from ._gui import (
    DashboardWriteError,
    FontError,
    FontFamilyError,
    FontLoadError,
    FontMissingError,
    FontRegisterError,
    GUIError,
)
from ._network import (
    ConnectionFailedError,
    HTTPStatusError,
    NetworkError,
    RequestTimeoutError,
)
from ._plugins import (
    PluginDependencyError,
    PluginImportError,
    PluginLoadError,
    PluginMissingError,
    PluginRoleError,
    PluginsError,
    PluginsMissingError,
    PluginSpecError,
)
from ._version import (
    LocalVersionError,
    NewVersionError,
    RemoteVersionError,
    VersionError,
)

__all__ = [
    # 异常文案
    "describe_error",
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
    "ConfigInputError",
    "ConfigOutputError",
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
    # 领域
    "DomainError",
    "MessageVanishedError",
    # GUI
    "GUIError",
    "DashboardWriteError",
    "FontError",
    "FontMissingError",
    "FontLoadError",
    "FontRegisterError",
    "FontFamilyError",
    # 插件
    "PluginsError",
    "PluginsMissingError",
    "PluginSpecError",
    "PluginMissingError",
    "PluginDependencyError",
    "PluginImportError",
    "PluginLoadError",
    "PluginRoleError",
    # 适配器
    "AdapterError",
    "AdapterMissingError",
    "AdapterOutOfDateError",
]
