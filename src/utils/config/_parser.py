# src/utils/config/_parser.py
"""配置解析（内部实现）

- 实现模板到 Schema 的解析
"""

import re
import tomllib
from pathlib import Path

from exceptions import ConfigParseError, ConfigTemplateMissingError

from .models import AppConfigData, AppSchema, FieldSchema, TabData, TabSchema


class ConfigParser:
    """模板配置解析器"""

    def __init__(self, example_path: Path) -> None:
        self._example_path = example_path
        self._raw_text = ""
        self._toml_data: AppConfigData = {}

    def parse(self) -> AppSchema:
        """解析为 AppSchema"""
        # 检查模板
        if not self._example_path.exists():
            raise ConfigTemplateMissingError() from None

        # 读取与解析
        try:
            self._raw_text = self._example_path.read_text(encoding="utf-8")

            with open(self._example_path, "rb") as f:
                self._toml_data = tomllib.load(f)

        except Exception as e:
            raise ConfigParseError() from e

        # 提取注释结构，组装 Schema
        return self._build_schema()

    def _build_schema(self) -> AppSchema:
        """组装 AppSchema"""
        schema: AppSchema = []
        raw_text = self._raw_text
        toml_data = self._toml_data

        # 找到所有注释标题块
        tab_pattern = re.compile(r"^# -{10} (.+?) -{10}", re.MULTILINE)
        tab_matches = list(tab_pattern.finditer(raw_text))

        # 找到所有 TOML section 头
        section_pattern = re.compile(r"^\[(.+?)\]", re.MULTILINE)
        section_matches = list(section_pattern.finditer(raw_text))

        # 按顺序配对注释块和 TOML section
        for i, (tab_match, sec_match) in enumerate(
            zip(tab_matches, section_matches, strict=False)
        ):
            tab_title = tab_match.group(1).strip()
            section_key = sec_match.group(1).strip()

            # 截取从 section 头到下一个 section 头之间的文本（包含字段定义）
            field_start = sec_match.end()
            field_end = (
                section_matches[i + 1].start()
                if i + 1 < len(section_matches)
                else len(raw_text)
            )
            field_text = raw_text[field_start:field_end]

            # 用实际的 section key 去 toml_data 取值
            toml_section = toml_data.get(section_key, {})

            fields = self._parse_fields(field_text, toml_section)
            if fields:
                schema.append(
                    TabSchema(title=tab_title, namespace=section_key, fields=fields)
                )

        return schema

    def _parse_fields(
        self, block_text: str, toml_section: TabData
    ) -> list[FieldSchema]:
        """解析单个 Tab 块中的字段"""
        fields: list[FieldSchema] = []
        lines = block_text.strip().split("\n")

        for key, default in toml_section.items():
            label = key  # 默认 label 就是 key 本身
            desc = ""  # 默认 desc 为空

            # 在原始文本中，寻找这个 key 上方的注释
            for idx, line in enumerate(lines):
                if line.strip().startswith(f"{key} ="):
                    # 防止格式被破坏影响启动
                    if (
                        idx >= 2
                        and lines[idx - 2].startswith("# ")
                        and lines[idx - 1].startswith("# ")
                    ):
                        label = lines[idx - 2].strip()[2:]
                        desc = lines[idx - 1].strip()[2:]
                    break  # 找到这个 key 后，跳出文本行循环，继续下一个 key

            fields.append(FieldSchema(key=key, label=label, desc=desc, default=default))

        return fields
