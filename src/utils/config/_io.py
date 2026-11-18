"""配置读写

- TOML 来源块与段名键值表的双向换算
- 全量原子保存与说明子表落盘
"""

import re
import tomllib
from collections.abc import Iterable, Mapping
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

from exceptions import ConfigInputError, ConfigMissingError, ConfigOutputError
from system.atomic_write import write_text_atomic

from ..logger import get_logger
from .models import AppConfigData, NotesBySection, SectionNotes, TabData

_logger = get_logger("Config")

# 每段之下的说明子表名，读盘摘出后不进内存
_NOTES_TABLE = "notes"

# 来源块的表名与块头里的身份码键名
_SOURCE_TABLE = "source"
_IDENTITY_KEY = "id"

# TOML bare key 字符集，集外的键名与表头段名一律加双引号
_BARE_KEY = re.compile(r"[A-Za-z0-9_-]+")

# basic string 的单字符转义，表外控制符走 \u00XX
_STRING_ESCAPES = {
    '"': '\\"',
    "\\": "\\\\",
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}


class ConfigIO:
    """配置文件读写器"""

    def __init__(self, config_path: Path) -> None:
        self._config_path = config_path

    def load(self) -> AppConfigData:
        """读取配置数据

        - 来源块按块内身份码拼成点分段名
        - 说明子表属文件说明，不进内存
        """
        return self._parse()[0]

    def load_notes(self) -> NotesBySection:
        """读取盘上的说明子表

        - 装配器据此判断说明要不要重打
        """
        return self._parse()[1]

    def save(self, config_data: AppConfigData, *, notes: NotesBySection) -> None:
        """全量保存配置

        - 整份原子替换，写不进即保持旧版原文
        """
        try:
            write_text_atomic(
                self._config_path, _render_config(config_data, notes=notes)
            )
        except Exception as e:
            raise ConfigOutputError() from e

    def _parse(self) -> tuple[AppConfigData, NotesBySection]:
        """读盘并摊平成段名键值表与说明子表两张"""
        if not self._config_path.exists():
            raise ConfigMissingError() from None

        try:
            raw_text = self._config_path.read_text(encoding="utf-8")
            flat: AppConfigData = {}
            notes: NotesBySection = {}
            _flatten(_sources(tomllib.loads(raw_text)), (), flat, notes)
            return flat, notes
        except Exception as e:
            raise ConfigInputError() from e


def _render_config(config_data: AppConfigData, *, notes: NotesBySection) -> str:
    """按段名渲染整份配置文本

    - 带前缀的段按来源归块，一块一个身份码，段块写在所属来源块内
    - 说明子表紧随本段之后
    - 无人认领的裸段仍写成顶层表，值原样留着
    """
    names = _write_order((*config_data, *notes))
    units = [
        unit
        for name in (n for n in names if "." not in n)
        for unit in _section_units((name,), config_data.get(name, {}), notes.get(name))
    ]
    for identity in _identities(names):
        units.append(f"[[{_SOURCE_TABLE}]]\n{_IDENTITY_KEY} = {_quoted_str(identity)}")
        for name in (n for n in names if n.rpartition(".")[0] == identity):
            units.extend(
                _section_units(
                    (_SOURCE_TABLE, name.rpartition(".")[2]),
                    config_data.get(name, {}),
                    notes.get(name),
                )
            )
    return ("\n\n".join(units) + "\n") if units else ""


def _identities(names: Iterable[str]) -> list[str]:
    """按首次出现排出的来源身份码，不带前缀的段不算"""
    found: list[str] = []
    for name in names:
        identity = name.rpartition(".")[0]
        if identity and identity not in found:
            found.append(identity)
    return found


def _section_units(
    header: tuple[str, ...], values: TabData, note: SectionNotes | None
) -> list[str]:
    """一段的表头块，带说明子表则紧随其后

    - 没键值又带说明的段不写父表头，只写说明那一层
    """
    units: list[str] = []
    if values or not note:
        units.append(_table_unit(header, values))
    if note:
        units.append(_table_unit((*header, _NOTES_TABLE), note))
    return units


def _table_unit(header: tuple[str, ...], values: TabData | SectionNotes) -> str:
    """一张表的表头行与键值行"""
    head = ".".join(_quoted_key(part) for part in header)
    rows = "".join(f"{_pair(key, value)}\n" for key, value in values.items())
    return f"[{head}]\n{rows}".rstrip("\n")


def _pair(key: str, value: Any) -> str:
    """一行键值"""
    return f"{_quoted_key(key)} = {_render_value(value)}"


def _render_value(value: Any) -> str:
    """值的 TOML 写法，成员值即落盘值

    - 空值没有 TOML 写法，连同不认识的类型一并抛错，由保存处整份拒写
    """
    if isinstance(value, str):
        return _quoted_str(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, (datetime, date, time)):
        stamp = value.isoformat()
        return f"{stamp[:-6]}Z" if stamp.endswith("+00:00") else stamp
    if isinstance(value, Mapping):
        return "{ " + ", ".join(_pair(key, item) for key, item in value.items()) + " }"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_render_value(item) for item in value) + "]"
    raise TypeError(f"配置值不支持 {type(value).__name__}")


def _quoted_key(key: str) -> str:
    """bare 字符集外的键名与表头段名加双引号"""
    return key if _BARE_KEY.fullmatch(key) else _quoted_str(key)


def _quoted_str(value: str) -> str:
    """basic string 单形：非 ASCII 原样出，控制符转义"""
    parts: list[str] = []
    for char in value:
        escape = _STRING_ESCAPES.get(char)
        if escape:
            parts.append(escape)
        elif char < " " or char == "\x7f":
            # 0x1B 不进转义表：TOML 无 \e 写法，写出字面反斜杠 e 就读不回来
            parts.append(f"\\u{ord(char):04x}")
        else:
            parts.append(char)
    return '"' + "".join(parts) + '"'


def _sources(document: Mapping[str, Any]) -> dict[str, Any]:
    """来源块换成段名到键值表的写法，段名带上块内身份码

    - 块内除身份码还有别的直接键即拒那一块，那些键按无人认领留下
    - 同一身份码第二次出现即拒那一块，账只记来源块身份，顶层裸段不算
    """
    converted: dict[str, Any] = {
        key: value for key, value in document.items() if key != _SOURCE_TABLE
    }
    blocks = document.get(_SOURCE_TABLE)
    if not isinstance(blocks, list):
        return converted
    first_seen: dict[str, int] = {}
    for index, element in enumerate(blocks):
        if not isinstance(element, Mapping):
            converted[f"{_SOURCE_TABLE}.{index}"] = {}
            continue
        identity = str(element.get(_IDENTITY_KEY, ""))
        if identity and identity in first_seen:
            _logger.error(
                f"配置来源块第 {index + 1} 块身份 {identity} 与第 "
                f"{first_seen[identity] + 1} 块重复，整块不进配置"
            )
            continue
        if identity:
            first_seen.setdefault(identity, index)
        stray = {
            key: value
            for key, value in element.items()
            if key != _IDENTITY_KEY and not isinstance(value, Mapping)
        }
        if stray:
            _logger.error(
                f"配置来源块第 {index + 1} 块除 {_IDENTITY_KEY} 还有 "
                f"{'、'.join(stray)}，整块不进配置"
            )
            converted[identity or f"{_SOURCE_TABLE}.{index}"] = stray
            continue
        for key, value in element.items():
            if key == _IDENTITY_KEY or not isinstance(value, Mapping):
                continue
            converted[f"{identity}.{key}"] = value
    return converted


def _flatten(
    source: Mapping[str, Any],
    prefix: tuple[str, ...],
    out: AppConfigData,
    notes: NotesBySection,
) -> None:
    """按点分把表摊平成段名到键值表

    - 中间层上的散落键单独立一段，值不丢
    - 说明子表摘出去单独交，不混进键值表
    """
    tables = {k: v for k, v in source.items() if isinstance(v, Mapping)}
    values = {k: v for k, v in source.items() if not isinstance(v, Mapping)}
    name = ".".join(prefix)
    note = tables.get(_NOTES_TABLE)
    if prefix and isinstance(note, Mapping):
        notes[name] = dict(note)
    subtables = {k: v for k, v in tables.items() if k != _NOTES_TABLE}
    if values or (prefix and not subtables):
        out[name] = values
    for key, child in subtables.items():
        _flatten(child, (*prefix, key), out, notes)


def _write_order(names: Iterable[str]) -> list[str]:
    """输出顺序跟随传入顺序，只把父段插到子段之前

    - 段名与说明子表同名，先去重
    """
    ordered: list[str] = []
    for name in dict.fromkeys(names):
        index = next(
            (i for i, done in enumerate(ordered) if done.startswith(f"{name}.")),
            len(ordered),
        )
        ordered.insert(index, name)
    return ordered
