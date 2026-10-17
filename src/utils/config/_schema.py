# src/utils/config/_schema.py
"""配置 Schema 组装

- 按平台从 domain 段表组装 AppSchema
- 结构与默认取 domain，标题与说明查 messages
"""

from core.domain import (
    TABS_BY_PLATFORM,
    ConfigKey,
    FieldSpec,
    Platform,
    ProxyMode,
    TabSpec,
)
from messages import ConfigMessage, DialogMessage

from .models import AppSchema, FieldSchema, TabSchema

# 枚举字段的值到界面文案映射，组装下拉选项用
_OPTION_LABELS: dict[ConfigKey, dict[str, str]] = {
    ConfigKey.PROXY_MODE: {
        ProxyMode.AUTO: DialogMessage.SETUP_MODE_AUTO,
        ProxyMode.CFG: DialogMessage.SETUP_MODE_CFG,
        ProxyMode.SYS: DialogMessage.SETUP_MODE_SYS,
        ProxyMode.DIRECT: DialogMessage.SETUP_MODE_DIRECT,
    },
}


def build_schema(platform: Platform) -> AppSchema:
    """按平台组装 AppSchema"""
    return [_build_tab(tab) for tab in TABS_BY_PLATFORM[platform]]


def _build_tab(tab: TabSpec) -> TabSchema:
    """组装单个页签"""
    return TabSchema(
        title=ConfigMessage.TAB_TITLES[tab.namespace],
        namespace=tab.namespace,
        fields=[_build_field(spec) for spec in tab.fields],
    )


def _build_field(spec: FieldSpec) -> FieldSchema:
    """组装单个字段"""
    return FieldSchema(
        key=spec.key,
        label=ConfigMessage.LABELS[spec.key],
        desc=ConfigMessage.DESCS[spec.key],
        default=spec.default,
        value_type=spec.value_type,
        options=_build_options(spec),
        required=spec.required,
        bounds=spec.bounds,
    )


def _build_options(spec: FieldSpec) -> tuple[tuple[str, str], ...]:
    """组装枚举字段的值与文案选项对"""
    if not spec.options:
        return ()
    labels = _OPTION_LABELS[spec.key]
    return tuple((str(value), labels[value]) for value in spec.options)
