"""配置 Schema 组装

- 按装配好的段表组装界面结构
"""

from collections.abc import Sequence

from finshin_sdk.domain import FieldSpec

from .models import AppSchema, FieldSchema, TabSchema
from .sources import AssembledSection


def build_schema(sections: Sequence[AssembledSection]) -> AppSchema:
    """按装配段表组装 AppSchema"""
    return [_build_tab(item) for item in sections]


def _build_tab(item: AssembledSection) -> TabSchema:
    """组装单个页签"""
    tab = item.spec
    return TabSchema(
        title=tab.title,
        section=item.name,
        group=item.identity,
        group_title=item.source_title,
        section_id=tab.section,
        fields=[_build_field(spec) for spec in tab.fields],
    )


def _build_field(spec: FieldSpec) -> FieldSchema:
    """组装单个字段"""
    return FieldSchema(
        key=spec.key,
        label=spec.label,
        desc=spec.desc,
        default=spec.default,
        value_type=spec.value_type,
        options=_build_options(spec),
        required=spec.required,
        bounds=spec.bounds,
    )


def _build_options(spec: FieldSpec) -> tuple[tuple[str, str], ...]:
    """组装枚举字段的值与文案选项对"""
    return tuple(
        (str(value), label)
        for value, label in zip(spec.options, spec.option_labels, strict=True)
    )
