# src/core/domain/config/_tg.py
"""Telegram 专属配置段

- 定义 proxy 段字段表
"""

from ._models import ConfigKey, ConfigNamespace, FieldSpec, ProxyMode, TabSpec

PROXY_TAB = TabSpec(
    namespace=ConfigNamespace.PROXY,
    fields=(
        FieldSpec(
            namespace=ConfigNamespace.PROXY,
            key=ConfigKey.PROXY_MODE,
            value_type=str,
            default=ProxyMode.AUTO,
            options=(
                ProxyMode.AUTO,
                ProxyMode.CFG,
                ProxyMode.SYS,
                ProxyMode.DIRECT,
            ),
        ),
        FieldSpec(
            namespace=ConfigNamespace.PROXY,
            key=ConfigKey.PROXY,
            value_type=str,
            default="",
        ),
    ),
)
