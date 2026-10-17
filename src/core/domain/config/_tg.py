# src/core/domain/config/_tg.py
"""Telegram 专属配置段

- 定义 proxy 段字段表
"""

from ._models import ConfigKey, ConfigSection, FieldSpec, ProxyMode, SectionSpec

PROXY_SECTION = SectionSpec(
    section=ConfigSection.PROXY,
    fields=(
        FieldSpec(
            section=ConfigSection.PROXY,
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
            section=ConfigSection.PROXY,
            key=ConfigKey.PROXY,
            value_type=str,
            default="",
        ),
    ),
)
