"""配置来源装配

- 定义来源类型、来源清单与装配结果
- 按来源顺序拼段表，段名带来源前缀
- 交出各段的默认值与说明子表
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import StrEnum

from finshin_sdk.domain import (
    ConfigKey,
    ConfigSection,
    FieldSpec,
    SectionSpec,
)

from ..logger import get_logger
from .models import AppConfigData, NotesBySection

_logger = get_logger("Config")


class SourceKind(StrEnum):
    """配置段的来源类型

    - 定义段名前缀首段的词表
    """

    ADAPTER = "adapter"
    PLUGIN = "plugin"
    CORE = "core"


@dataclass(frozen=True, slots=True)
class ConfigSource:
    """一份来源交出的配置段

    - 身份码为平台码或插件名，本体侧不带
    - 标题随声明交出，定面板左列那一行
    - 交出顺序即面板页签顺序
    """

    kind: SourceKind
    code: str
    title: str
    sections: tuple[SectionSpec, ...]


@dataclass(frozen=True, slots=True)
class AssembledSection:
    """装配后的一个配置段

    - name 为带来源前缀的段名
    - identity 为来源身份串，source_title 为该来源交出的标题，两者定面板左列
    """

    name: str
    identity: str
    source_title: str
    spec: SectionSpec


@dataclass(frozen=True, slots=True)
class ConfigPlan:
    """装配交出的段表

    - 段顺序即面板页签顺序
    """

    sections: tuple[AssembledSection, ...]

    def defaults(self) -> AppConfigData:
        """逐来源交出各段的默认值"""
        return {
            item.name: {fld.key: fld.default for fld in item.spec.fields}
            for item in self.sections
        }

    def notes(self) -> NotesBySection:
        """按交出模板算各段的说明子表"""
        return {
            item.name: {fld.key: fld.desc for fld in item.spec.fields if fld.desc}
            for item in self.sections
        }


_PLAN: ConfigPlan | None = None  # 最近一次装配的段表


def assemble(sources: Sequence[ConfigSource]) -> ConfigPlan:
    """按来源顺序拼段表

    - 同一身份码被两份认领时采纳先交的那份，后交的一份当场点名
    - 同一来源同一段里键重复时采纳先出现的一项，后出现的当场点名
    """
    items: list[AssembledSection] = []
    owners: dict[str, str] = {}
    for source in sources:
        identity = _identity(source)
        names = "、".join(str(sec.section) for sec in source.sections)
        if identity in owners:
            _logger.error(
                f"配置来源 {identity} 被两份认领，"
                f"先交的 {owners[identity]} 进配置，这份的 {names} 不进"
            )
            continue
        owners[identity] = names
        items.extend(
            AssembledSection(
                name=section_name(identity, sec.section),
                identity=identity,
                source_title=source.title,
                spec=_unique_fields(identity, sec),
            )
            for sec in source.sections
        )
    return ConfigPlan(tuple(items))


def use_plan(plan: ConfigPlan) -> None:
    """记下本次装配的段表，供取值、渲染与写回取用"""
    global _PLAN
    _PLAN = plan


def current_plan() -> ConfigPlan | None:
    """取最近一次装配的段表，还没装配即无值"""
    return _PLAN


def section_name(source: str, section: ConfigSection) -> str:
    """来源身份码与段名拼成盘上段名

    - 装配写法只此一处，取值与写回共用
    """
    return f"{source}.{section}"


def _identity(source: ConfigSource) -> str:
    """来源的身份码整串，本体侧只有来源类型一段"""
    return (
        str(source.kind)
        if source.kind == SourceKind.CORE
        else f"{source.kind}.{source.code}"
    )


def _unique_fields(identity: str, spec: SectionSpec) -> SectionSpec:
    """段内重复的键只留先出现的一项，后出现的点名拒收"""
    kept: list[FieldSpec] = []
    seen: set[ConfigKey] = set()
    for field in spec.fields:
        if field.key in seen:
            _logger.error(
                f"配置来源 {identity} 的段 {spec.section} 里键 {field.key} 重复，"
                "后出现的这一项不进配置"
            )
            continue
        seen.add(field.key)
        kept.append(field)
    if len(kept) == len(spec.fields):
        return spec
    return replace(spec, fields=tuple(kept))
