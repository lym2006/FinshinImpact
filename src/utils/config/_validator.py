# src/utils/config/_validator.py
"""配置校验

- 按字段值类型与数值区间校验
- 按字段必填标记判定缺键与空值
"""

from skin.messages import ConfigMessage

from .models import AppConfigData, AppSchema, FieldErrors, is_blank

# 值类型 → 校验规则说明
_TYPE_NAMES = {
    float: "float",
    str: "str",
    list: "list",
    bool: "bool",
}


def validate_types(schema: AppSchema, data: AppConfigData) -> FieldErrors:
    """按 schema 校验各字段类型与数值区间

    - 必填键缺键或留空报必填文案
    - 非必填键缺失静默放行，由运行期回退默认值
    """
    errors: FieldErrors = {}

    for tab in schema:
        section_data = data.get(tab.section, {})
        for fld in tab.fields:
            if fld.key not in section_data:
                if fld.required:
                    errors[fld.key] = ConfigMessage.REQUIRED_MARK
                continue

            value = section_data[fld.key]
            if fld.required and is_blank(value):
                errors[fld.key] = ConfigMessage.REQUIRED_MARK
                continue

            expected = fld.value_type
            if expected not in _TYPE_NAMES:
                continue

            if not _match(value, expected):
                tname = _TYPE_NAMES[expected]
                errors[fld.key] = f"类型应为 {tname}，当前 {value!r}"
                continue

            if fld.options and value not in {k for k, _ in fld.options}:
                legal = " / ".join(v for v, _ in fld.options)
                errors[fld.key] = f"取值应为 {legal} 之一，当前 {value!r}"
                continue

            if fld.bounds and expected is float:
                lo, hi = fld.bounds
                if not lo <= value <= hi:  # type: ignore[operator]
                    errors[fld.key] = f"取值应在 {lo:g}~{hi:g}，当前 {value!r}"

    return errors


def _match(value: object, expected: type) -> bool:
    """单值类型判定"""
    if value is None:
        return False

    if expected is bool:
        return isinstance(value, bool)
    if expected is float:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected is list:
        return isinstance(value, list) and all(isinstance(x, str) for x in value)
    return isinstance(value, expected)
