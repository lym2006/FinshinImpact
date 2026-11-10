# src/utils/config/_differ.py
"""配置比对

- 新旧配置的逐项差异
"""

from .models import AppConfigData, AppSchema, ConfigValue

_LType = list[tuple[str, ConfigValue, ConfigValue]]


def compare_configs(
    schema: AppSchema,
    original: AppConfigData,
    modified: AppConfigData,
) -> tuple[AppConfigData, _LType]:
    """提取配置变更

    - 遍历结构表，逐字段比对
    """
    changes: AppConfigData = {}
    logs: _LType = []
    for tab in schema:
        section = tab.section
        section_changes = {}
        for field in tab.fields:
            ori = original.get(section, {}).get(field.key)
            mod = modified.get(section, {}).get(field.key)
            if ori != mod:
                section_changes[field.key] = mod
                logs.append((field.label, ori, mod))
        if section_changes:
            changes[section] = section_changes

    return changes, logs
