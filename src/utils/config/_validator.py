# src/utils/config/_validator.py
"""配置校验（内部实现）

- 实现按默认值类型的校验
- 实现必填项的存在与非空判定
"""

from .models import (
    REQUIRED_KEYS,
    REQUIRED_MARK,
    AppConfigData,
    AppSchema,
    is_blank,
)

# schema default 类型 → 校验规则说明
_TYPE_NAMES = {
    float: "float",
    str: "str",
    list: "list",
    bool: "bool",
}

# 数值区间（闭区间，仅 float）：temperature 上限 2 为 OpenAI 兼容规范
_BOUNDS: dict[str, tuple[float, float]] = {
    "temperature": (0.0, 2.0),
    "network_timeout": (1.0, 600.0),
    "clearup": (0.1, 720.0),
    "waiting": (0.1, 720.0),
}


def validate_types(schema: AppSchema, data: AppConfigData) -> dict[str, str]:
    """按 schema 校验各字段类型与数值区间

    必填键缺键或留空报必填文案。
    非必填键缺失静默放行，由运行期回退模板默认值。
    """
    errors: dict[str, str] = {}

    for tab in schema:
        ns_data = data.get(tab.namespace, {})
        for fld in tab.fields:
            required = f"{tab.namespace}.{fld.key}" in REQUIRED_KEYS

            if fld.key not in ns_data:
                if required:
                    errors[fld.key] = REQUIRED_MARK
                continue

            value = ns_data[fld.key]
            if required and is_blank(value):
                errors[fld.key] = REQUIRED_MARK
                continue

            expected = type(fld.default)
            if fld.default is None or expected not in _TYPE_NAMES:
                continue  # 无默认值的字段不强制类型

            if not _match(value, expected):
                tname = _TYPE_NAMES[expected]
                errors[fld.key] = f"类型应为 {tname}，当前 {value!r}"
                continue

            bounds = _BOUNDS.get(fld.key)
            if bounds and expected is float:
                lo, hi = bounds
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
