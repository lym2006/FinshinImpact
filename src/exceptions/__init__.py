"""异常聚合包

- 代发全部自定义异常族
- 代发异常文案查询
"""

from ._adapter import (
    AdapterError,
    AdapterImportError,
    AdapterMissingError,
    AdapterOutOfDateError,
)
from ._config import (
    ConfigAttrError,
    ConfigError,
    ConfigInputError,
    ConfigMissingError,
    ConfigOutputError,
    ConfigPathMissingError,
    ProfileMissingError,
)
from ._describe import describe_error
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
    PluginEntryError,
    PluginImportError,
    PluginLoadError,
    PluginManifestError,
    PluginMissingError,
    PluginRoleError,
    PluginsError,
    PluginsMissingError,
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
    "PluginEntryError",
    "PluginMissingError",
    "PluginDependencyError",
    "PluginImportError",
    "PluginLoadError",
    "PluginManifestError",
    "PluginRoleError",
    # 适配器
    "AdapterError",
    "AdapterImportError",
    "AdapterMissingError",
    "AdapterOutOfDateError",
]
