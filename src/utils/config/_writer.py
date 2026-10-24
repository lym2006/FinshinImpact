# src/utils/config/_writer.py
"""配置初值生成

- 按平台段表生成 config.toml 初值文本
"""

import tomlkit

from core.domain import SECTIONS_BY_PLATFORM, Platform


def render_config(platform: Platform) -> str:
    """按平台生成初值配置文本

    - 段顺序即表顺序，QQ 表无 proxy 段
    """
    doc = tomlkit.document()
    for tab in SECTIONS_BY_PLATFORM[platform]:
        table = tomlkit.table()
        for spec in tab.fields:
            table[spec.key] = spec.default
        doc.add(tab.section, table)
    return tomlkit.dumps(doc)
