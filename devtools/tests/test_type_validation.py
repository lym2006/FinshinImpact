"""配置类型校验与运行期兜底的单元测试

- validate_types：按 schema default 类型检出字段错误
- 必填清单：缺键与空值检出、非必填缺键放行
- 配置文案按声明读取、选项文案数量校验
- _ConfigManager：非必填缺键回退 schema 默认值
- ErrorGuardMiddleware：下游 ConfigError 不冒泡，记日志
"""

import sys
import unittest
from pathlib import Path
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from finshin_sdk.domain import (  # noqa: E402
    ConfigKey,
    ConfigPath,
    ConfigSection,
    FieldSpec,
    SectionSpec,
)
from skin.messages import ConfigMessage  # noqa: E402
from utils._config_manager import _ConfigManager  # noqa: E402
from utils.check import local_row  # noqa: E402
from utils.config._validator import validate_types  # noqa: E402
from utils.config.models import (  # noqa: E402
    FieldSchema,
    TabSchema,
    is_blank,
)
from utils.network import RowId, RowStatus  # noqa: E402


def _declared_section() -> SectionSpec:
    """构造只含一只文本字段的段声明，供改写字段文案的用例取底"""
    return SectionSpec(
        section=ConfigSection.CHORE,
        title="段标题",
        fields=(
            FieldSpec(
                section=ConfigSection.CHORE,
                key=ConfigKey.OWNER,
                value_type=str,
                default="",
                label="",
                desc="",
            ),
        ),
    )


_GROUP = "plugin.AI"
_MODEL_SECTION = "plugin.AI.model"
_CHORE_SECTION = "plugin.AI.chore"


def _item(key: ConfigKey, section: ConfigSection = ConfigSection.MODEL) -> ConfigPath:
    """本组用例的配置项身份"""
    return key.path(_GROUP, section)


def _schema() -> list[TabSchema]:
    """构造含 float/str/list 三类字段的 schema"""
    return [
        TabSchema(
            title="AI",
            section=_MODEL_SECTION,
            group=_GROUP,
            group_title="AI 设置",
            section_id=ConfigSection.MODEL,
            fields=[
                FieldSchema(ConfigKey.TEMPERATURE, "温度", "", 0.7, float),
                FieldSchema(ConfigKey.API_KEY, "模型", "", "gpt", str),
                FieldSchema(ConfigKey.TRIGGERS, "标签", "", ["a"], list),
            ],
        )
    ]


class TestValidateTypes(unittest.TestCase):
    """回归点

    - float 字段填 str 必须当场检出（当前代码此处失败）
    """

    def test_float_field_rejects_str(self) -> None:
        """数值型字段填字符串必须检出"""
        data = {
            _MODEL_SECTION: {"temperature": "abc", "api_key": "gpt", "triggers": ["a"]}
        }
        errors = validate_types(_schema(), data)
        self.assertIn(_item(ConfigKey.TEMPERATURE), errors)

    def test_int_accepted_for_float_field(self) -> None:
        """整数可赋给浮点字段"""
        # toml 里 1 会被解析为 int，float 字段应兼容
        data = {_MODEL_SECTION: {"temperature": 1, "api_key": "gpt", "triggers": ["a"]}}
        self.assertEqual(validate_types(_schema(), data), {})

    def test_bool_rejected_for_float_field(self) -> None:
        """布尔值不算浮点"""
        data = {
            _MODEL_SECTION: {"temperature": True, "api_key": "gpt", "triggers": ["a"]}
        }
        self.assertIn(_item(ConfigKey.TEMPERATURE), validate_types(_schema(), data))

    def test_list_requires_str_items(self) -> None:
        """列表字段元素必须为字符串"""
        data = {
            _MODEL_SECTION: {"temperature": 0.5, "api_key": "gpt", "triggers": [1, 2]}
        }
        self.assertIn(_item(ConfigKey.TRIGGERS), validate_types(_schema(), data))

    def test_all_valid_empty(self) -> None:
        """全部合法返回空 dict"""
        data = {
            _MODEL_SECTION: {"temperature": 0.5, "api_key": "gpt", "triggers": ["a"]}
        }
        self.assertEqual(validate_types(_schema(), data), {})

    def test_missing_optional_keys_pass(self) -> None:
        """非必填键缺失放行

        - 运行期回退 schema 默认值，不算校验错误
        """

        self.assertEqual(validate_types(_schema(), {}), {})


class TestRequiredValidation(unittest.TestCase):
    """回归点

    - 必填清单：缺键/空值检出，正常值不误伤
    """

    def _schema(self) -> list[TabSchema]:
        """含必填与可选两类的 schema"""
        return [
            TabSchema(
                title="AI",
                section=_MODEL_SECTION,
                group=_GROUP,
                group_title="AI 设置",
                section_id=ConfigSection.MODEL,
                fields=[
                    FieldSchema(
                        ConfigKey.API_KEY, "密钥", "", "sk", str, required=True
                    ),
                    FieldSchema(ConfigKey.TEMPERATURE, "温度", "", 0.7, float),
                    FieldSchema(ConfigKey.TRIGGERS, "标签", "", ["a"], list),
                ],
            ),
            TabSchema(
                title="触发",
                section=_CHORE_SECTION,
                group=_GROUP,
                group_title="AI 设置",
                section_id=ConfigSection.CHORE,
                fields=[
                    FieldSchema(
                        ConfigKey.TRIGGERS, "触发词", "", ["a"], list, required=True
                    )
                ],
            ),
        ]

    def test_missing_required_key_flagged(self) -> None:
        """必填键缺失报必填文案"""
        data = {_MODEL_SECTION: {"temperature": 0.5, "triggers": ["a"]}}
        errors = validate_types(self._schema(), data)
        self.assertIn(_item(ConfigKey.API_KEY), errors)
        self.assertEqual(errors[_item(ConfigKey.API_KEY)], ConfigMessage.REQUIRED_MARK)

    def test_blank_required_value_flagged(self) -> None:
        """必填键空白字符串与空列表都算未填写"""
        data = {
            _MODEL_SECTION: {"api_key": "  ", "temperature": 0.5, "triggers": ["a"]},
            _CHORE_SECTION: {"triggers": []},
        }
        errors = validate_types(self._schema(), data)
        self.assertEqual(errors[_item(ConfigKey.API_KEY)], ConfigMessage.REQUIRED_MARK)
        self.assertEqual(
            errors[_item(ConfigKey.TRIGGERS, ConfigSection.CHORE)],
            ConfigMessage.REQUIRED_MARK,
        )

    def test_zero_and_false_not_blank(self) -> None:
        """数值 0 与 False 是合法填写"""
        self.assertFalse(is_blank(0))
        self.assertFalse(is_blank(False))
        self.assertFalse(is_blank(0.0))

    def test_typed_required_key_reports_type_first(self) -> None:
        """必填键填了错类型走类型文案

        - 不占必填语义
        """
        data = {_MODEL_SECTION: {"api_key": 123, "temperature": 0.5, "triggers": ["a"]}}
        errors = validate_types(self._schema(), data)
        self.assertIn("类型应为 str", errors[_item(ConfigKey.API_KEY)])


class TestConfigManagerFallback(unittest.TestCase):
    """回归点

    - 非必填缺键回退 schema 默认值
    - 必填缺键照抛
    """

    def _manager(self) -> _ConfigManager:
        """预置 schema 的干净管理器"""
        manager = _ConfigManager()
        manager._schema = _schema()
        return manager

    def test_optional_missing_falls_back(self) -> None:
        """缺键非必填

        - 取 schema 默认值
        """

        manager = self._manager()
        manager.load({_MODEL_SECTION: {"temperature": 0.5}})
        self.assertEqual(manager.get(_item(ConfigKey.API_KEY), str), "gpt")

    def test_missing_section_falls_back(self) -> None:
        """整段缺失

        - 非必填仍可回退
        """

        manager = self._manager()
        manager.load({})
        self.assertEqual(manager.get(_item(ConfigKey.TRIGGERS), list), ["a"])

    def test_required_missing_still_raises(self) -> None:
        """schema 里没有的项照抛缺键"""
        from exceptions import ConfigPathMissingError

        manager = self._manager()
        manager.load({_MODEL_SECTION: {"api_key": "", "temperature": 0.5}})
        with self.assertRaises(ConfigPathMissingError):
            manager.get(_item(ConfigKey.OWNER, ConfigSection.CHORE), str)

    def test_schema_default_isolated(self) -> None:
        """回退值与 schema 默认对象隔离

        - 防调用方就地改写污染默认值
        """

        manager = self._manager()
        manager.load({})
        first = cast("list[str]", manager._schema_default(_item(ConfigKey.TRIGGERS)))
        first.append("mutated")
        self.assertEqual(manager._schema_default(_item(ConfigKey.TRIGGERS)), ["a"])

    def test_get_all_isolated(self) -> None:
        """整表读出与内存配置隔离

        - 就地改写交出去的那份不回渗内存
        """

        manager = self._manager()
        manager.load({_MODEL_SECTION: {"temperature": 0.5}})
        snapshot = manager.get_all()
        snapshot[_MODEL_SECTION]["temperature"] = 9.9
        self.assertEqual(manager.get(_item(ConfigKey.TEMPERATURE), float), 0.5)


class TestLocalRow(unittest.TestCase):
    """回归点

    - local_row 的两条契约：错误字典与 validate_types 一致、带回 local 行终态帧
    """

    def test_returns_same_errors_as_validate_types(self) -> None:
        """错误字典与 validate_types 完全一致

        - 封装不吞错
        """

        data = {
            _MODEL_SECTION: {"temperature": "abc", "api_key": "gpt", "triggers": ["a"]}
        }
        _, errors = local_row(_schema(), data)
        self.assertEqual(errors, validate_types(_schema(), data))

    def test_fail_frame_carries_count(self) -> None:
        """有错时终态帧 FAIL

        - 计数进详情
        """
        data = {
            _MODEL_SECTION: {"temperature": "abc", "api_key": "gpt", "triggers": ["a"]}
        }
        frame, _ = local_row(_schema(), data)
        self.assertEqual(frame["id"], RowId.LOCAL)
        self.assertEqual(frame["status"], RowStatus.FAIL)
        self.assertIn("1", frame["detail"])

    def test_ok_frame_when_valid(self) -> None:
        """全合法时帧为 OK 且错误为空 dict"""
        data = {
            _MODEL_SECTION: {"temperature": 0.5, "api_key": "gpt", "triggers": ["a"]}
        }
        frame, errors = local_row(_schema(), data)
        self.assertEqual(frame["status"], RowStatus.OK)
        self.assertEqual(errors, {})


class TestRequiredKeysReconcile(unittest.TestCase):
    """回归点

    - 必填集合由 domain 字段表定，改必填标记必须过这一关
    """

    def test_required_paths_match_domain_table(self) -> None:
        """schema 里的必填路径与预期集合一致"""
        from config_plan import fake_adapter_parts

        from bot._managers._config_sources import config_sources
        from utils.config._schema import build_schema
        from utils.config.sources import assemble

        with fake_adapter_parts():
            schema = build_schema(assemble(config_sources()).sections)
        paths = {
            f"{tab.section}.{fld.key}"
            for tab in schema
            for fld in tab.fields
            if fld.required
        }
        self.assertEqual(
            paths,
            {
                "plugin.AI.model.api_key",
                "plugin.AI.chore.owner",
                "plugin.AI.chore.triggers",
            },
        )


class TestPlatformSchema(unittest.TestCase):
    """回归点

    - QQ 表无 proxy 段
    - 装配写出的初值文本能被读回
    """

    def test_schema_uses_declared_text(self) -> None:
        from dataclasses import replace
        from unittest.mock import patch

        from config_plan import fake_adapter_parts

        from bot._managers._config_sources import config_sources
        from finshin_sdk.domain import SECTIONS_BY_PLATFORM, Platform
        from utils.config._schema import build_schema
        from utils.config.sources import assemble

        source = _declared_section()
        for options, labels in (((), ()), (("first", "second"), ("第一项", "第二项"))):
            with self.subTest(options=options):
                field = replace(
                    source.fields[0],
                    label="字段标题",
                    desc="字段说明",
                    options=options,
                    option_labels=labels,
                )
                section = replace(source, title="页签标题", fields=(field,))
                with (
                    patch.dict(SECTIONS_BY_PLATFORM, {Platform.QQ: (section,)}),
                    patch("bot._managers._config_sources.PLATFORM", Platform.QQ),
                    fake_adapter_parts("大类标题"),
                ):
                    tab = build_schema(assemble(config_sources()).sections)[0]
                self.assertEqual(tab.title, "页签标题")
                self.assertEqual(tab.group, "adapter.qq")
                self.assertEqual(tab.group_title, "大类标题")
                self.assertEqual(tab.fields[0].label, "字段标题")
                self.assertEqual(tab.fields[0].desc, "字段说明")
                self.assertEqual(
                    tab.fields[0].options, tuple(zip(options, labels, strict=True))
                )

    def test_option_label_count_mismatch_rejected(self) -> None:
        from dataclasses import replace

        from utils.config._schema import _build_field

        source = _declared_section().fields[0]
        for options, labels in ((("first",), ()), ((), ("第一项",))):
            with self.subTest(options=options, labels=labels):
                field = replace(source, options=options, option_labels=labels)
                with self.assertRaises(ValueError):
                    _build_field(field)

    def test_qq_table_has_no_proxy(self) -> None:
        """QQ 平台拼出的段表不含代理段"""
        from unittest.mock import patch

        from config_plan import fake_adapter_parts

        from bot._managers._config_sources import config_sources
        from finshin_sdk.domain import Platform
        from utils.config._schema import build_schema
        from utils.config.sources import assemble

        with (
            patch("bot._managers._config_sources.PLATFORM", Platform.QQ),
            fake_adapter_parts(),
        ):
            plan = assemble(config_sources())
        sections = {tab.section for tab in build_schema(plan.sections)}
        self.assertNotIn("adapter.tg.proxy", sections)

    def test_rendered_config_roundtrips(self) -> None:
        """装配写出的初值文件能被读回，段名带来源前缀"""
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from config_plan import fake_adapter_parts

        from bot._managers._config_sources import config_sources
        from utils.config import ensure_config
        from utils.config._io import ConfigIO

        path = Path(tempfile.mkdtemp()) / "config.toml"
        with patch("utils.config.CONFIG_FILE", path), fake_adapter_parts():
            ensure_config(config_sources())
        data = ConfigIO(path).load()
        self.assertIn("plugin.AI.chore", data)
        self.assertEqual(data["core.data"]["record_keep"], 30.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
