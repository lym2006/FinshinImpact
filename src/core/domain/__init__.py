# src/core/domain/__init__.py
"""领域类型门面

- 定义业务类型，将不同平台的原始类型归一化
"""

from ._adapter import (
    ADAPTER_ENTRY_MODULE,
    ADAPTER_MANIFEST_FIELDS,
    ADAPTER_MANIFEST_FILE,
    ADAPTERS_PKG,
    AdapterFieldSpec,
    AdapterManifestKey,
)
from ._command import BoundCommand, CommandFlag, StepInput, bind_command, is_flag_name
from ._container import make_container
from ._content import ContentKind
from ._fields import FieldKey
from ._platform import ChatScope, Platform, make_profile_code, platform_of_profile
from ._plugin import (
    BUNDLED_PLUGIN_PRIORITY,
    INSTALLED_PLUGINS_NAME,
    MANIFEST_FIELDS,
    PLUGINS_PKG,
    CommandPriority,
    CommandTaken,
    HelpKey,
    ManifestFieldSpec,
    ManifestKey,
    PlatformTiming,
    PluginBackground,
    PluginClaim,
    PluginFileName,
    PluginMark,
    PluginPredicate,
    PluginRoute,
    PluginSpec,
    PluginTiming,
    PluginTimingRun,
    RouteSink,
    StateKey,
    TaskHandler,
    TaskRun,
    is_enabled,
    resolve_claims,
)
from ._role import ChatRole, CommandRole
from ._task import TaskKind, TaskPayload, TaskStatus
from .config import (
    SECTIONS_BY_PLATFORM,
    ConfigGroup,
    ConfigKey,
    ConfigSection,
    ConfigValue,
    FieldSpec,
    ProxyMode,
    SectionSpec,
)

__all__ = [
    # 字段创建
    "make_container",
    # 实例身份码
    "make_profile_code",
    "platform_of_profile",
    # 平台
    "Platform",
    "ChatScope",
    # 适配器
    "ADAPTERS_PKG",
    "ADAPTER_ENTRY_MODULE",
    "ADAPTER_MANIFEST_FILE",
    "AdapterManifestKey",
    "AdapterFieldSpec",
    "ADAPTER_MANIFEST_FIELDS",
    # 插件
    "PLUGINS_PKG",
    "INSTALLED_PLUGINS_NAME",
    "PlatformTiming",
    "PluginBackground",
    "PluginPredicate",
    "PluginRoute",
    "PluginSpec",
    "PluginTiming",
    "PluginTimingRun",
    "CommandPriority",
    "CommandTaken",
    "PluginClaim",
    "PluginFileName",
    "PluginMark",
    "ManifestKey",
    "ManifestFieldSpec",
    "MANIFEST_FIELDS",
    "BUNDLED_PLUGIN_PRIORITY",
    "HelpKey",
    "StateKey",
    "RouteSink",
    "TaskHandler",
    "TaskRun",
    "is_enabled",
    "resolve_claims",
    # 内容与角色
    "ContentKind",
    "ChatRole",
    "CommandRole",
    # 命令
    "CommandFlag",
    "StepInput",
    "BoundCommand",
    "bind_command",
    "is_flag_name",
    # 任务
    "TaskPayload",
    "TaskKind",
    "TaskStatus",
    # 探测字段键
    "FieldKey",
    # 配置结构
    "ConfigValue",
    "ConfigSection",
    "ConfigKey",
    "ConfigGroup",
    "ProxyMode",
    "FieldSpec",
    "SectionSpec",
    "SECTIONS_BY_PLATFORM",
]
