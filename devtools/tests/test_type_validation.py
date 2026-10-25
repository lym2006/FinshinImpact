# devtools/tests/test_type_validation.py
"""配置类型校验与运行期兜底的单元测试

- validate_types：按 schema default 类型检出字段错误
- 必填清单：缺键与空值检出、非必填缺键放行
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


def _schema() -> list[TabSchema]:
    """构造含 float/str/list 三类字段的 schema"""
    return [
        TabSchema(
            title="AI",
            section="ai",
            fields=[
                FieldSchema("temperature", "温度", "", 0.7, float),
                FieldSchema("model", "模型", "", "gpt", str),
                FieldSchema("tags", "标签", "", ["a"], list),
            ],
        )
    ]


class TestValidateTypes(unittest.TestCase):
    """回归点

    - float 字段填 str 必须当场检出（当前代码此处失败）
    """

    def test_float_field_rejects_str(self) -> None:
        """数值型字段填字符串必须检出"""
        data = {"ai": {"temperature": "abc", "model": "gpt", "tags": ["a"]}}
        errors = validate_types(_schema(), data)
        self.assertIn("temperature", errors)

    def test_int_accepted_for_float_field(self) -> None:
        """整数可赋给浮点字段"""
        # toml 里 1 会被解析为 int，float 字段应兼容
        data = {"ai": {"temperature": 1, "model": "gpt", "tags": ["a"]}}
        self.assertEqual(validate_types(_schema(), data), {})

    def test_bool_rejected_for_float_field(self) -> None:
        """布尔值不算浮点"""
        data = {"ai": {"temperature": True, "model": "gpt", "tags": ["a"]}}
        self.assertIn("temperature", validate_types(_schema(), data))

    def test_list_requires_str_items(self) -> None:
        """列表字段元素必须为字符串"""
        data = {"ai": {"temperature": 0.5, "model": "gpt", "tags": [1, 2]}}
        self.assertIn("tags", validate_types(_schema(), data))

    def test_all_valid_empty(self) -> None:
        """全部合法返回空 dict"""
        data = {"ai": {"temperature": 0.5, "model": "gpt", "tags": ["a"]}}
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
                section="ai",
                fields=[
                    FieldSchema("api_key", "密钥", "", "sk", str, required=True),
                    FieldSchema("temperature", "温度", "", 0.7, float),
                    FieldSchema("tags", "标签", "", ["a"], list),
                ],
            ),
            TabSchema(
                title="触发",
                section="chore",
                fields=[
                    FieldSchema("triggers", "触发词", "", ["a"], list, required=True)
                ],
            ),
        ]

    def test_missing_required_key_flagged(self) -> None:
        """必填键缺失报必填文案"""
        data = {"ai": {"temperature": 0.5, "tags": ["a"]}}
        errors = validate_types(self._schema(), data)
        self.assertIn("api_key", errors)
        self.assertEqual(errors["api_key"], ConfigMessage.REQUIRED_MARK)

    def test_blank_required_value_flagged(self) -> None:
        """必填键空白字符串与空列表都算未填写"""
        data = {
            "ai": {"api_key": "  ", "temperature": 0.5, "tags": ["a"]},
            "chore": {"triggers": []},
        }
        errors = validate_types(self._schema(), data)
        self.assertEqual(errors["api_key"], ConfigMessage.REQUIRED_MARK)
        self.assertEqual(errors["triggers"], ConfigMessage.REQUIRED_MARK)

    def test_zero_and_false_not_blank(self) -> None:
        """数值 0 与 False 是合法填写"""
        self.assertFalse(is_blank(0))
        self.assertFalse(is_blank(False))
        self.assertFalse(is_blank(0.0))

    def test_typed_required_key_reports_type_first(self) -> None:
        """必填键填了错类型走类型文案

        - 不占必填语义
        """
        data = {"ai": {"api_key": 123, "temperature": 0.5, "tags": ["a"]}}
        errors = validate_types(self._schema(), data)
        self.assertIn("类型应为 str", errors["api_key"])


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
        manager.load({"ai": {"temperature": 0.5}})
        self.assertEqual(manager.get("ai.model", str), "gpt")

    def test_missing_section_falls_back(self) -> None:
        """整段缺失

        - 非必填仍可回退
        """

        manager = self._manager()
        manager.load({})
        self.assertEqual(manager.get("ai.tags", list), ["a"])

    def test_required_missing_still_raises(self) -> None:
        """必填键缺失必须抛缺键"""
        from exceptions import ConfigPathMissingError

        manager = self._manager()
        manager.load({"basic": {"proxy": ""}})
        with self.assertRaises(ConfigPathMissingError):
            manager.get("basic.telegram_token", str)

    def test_schema_default_isolated(self) -> None:
        """回退值与 schema 默认对象隔离

        - 防调用方就地改写污染默认值
        """

        manager = self._manager()
        manager.load({})
        first = cast("list[str]", manager._schema_default("ai.tags"))
        first.append("mutated")
        self.assertEqual(manager._schema_default("ai.tags"), ["a"])


class TestLocalRow(unittest.TestCase):
    """回归点

    - local_row 的两条契约：错误字典与 validate_types 一致、带回 local 行终态帧
    """

    def test_returns_same_errors_as_validate_types(self) -> None:
        """错误字典与 validate_types 完全一致

        - 封装不吞错
        """

        data = {"ai": {"temperature": "abc", "model": "gpt", "tags": ["a"]}}
        _, errors = local_row(_schema(), data)
        self.assertEqual(errors, validate_types(_schema(), data))

    def test_fail_frame_carries_count(self) -> None:
        """有错时终态帧 FAIL

        - 计数进详情
        """
        data = {"ai": {"temperature": "abc", "model": "gpt", "tags": ["a"]}}
        frame, _ = local_row(_schema(), data)
        self.assertEqual(frame["id"], RowId.LOCAL)
        self.assertEqual(frame["status"], RowStatus.FAIL)
        self.assertIn("1", frame["detail"])

    def test_ok_frame_when_valid(self) -> None:
        """全合法时帧为 OK 且错误为空 dict"""
        data = {"ai": {"temperature": 0.5, "model": "gpt", "tags": ["a"]}}
        frame, errors = local_row(_schema(), data)
        self.assertEqual(frame["status"], RowStatus.OK)
        self.assertEqual(errors, {})


class TestRequiredKeysReconcile(unittest.TestCase):
    """回归点

    - 必填集合由 domain 字段表定，改必填标记必须过这一关
    """

    def test_required_paths_match_domain_table(self) -> None:
        """schema 里的必填路径与预期集合一致"""
        from utils.config import get_schema

        paths = {
            f"{tab.section}.{fld.key}"
            for tab in get_schema()
            for fld in tab.fields
            if fld.required
        }
        self.assertEqual(paths, {"ai.api_key", "chore.owner", "chore.triggers"})


class TestPlatformSchema(unittest.TestCase):
    """回归点

    - QQ 表无 proxy 段
    - 按平台生成的初值文本能被读回
    """

    def test_qq_table_has_no_proxy(self) -> None:
        """QQ 平台段表不含代理段"""
        from core.domain import Platform
        from utils.config._schema import build_schema

        sections = {tab.section for tab in build_schema(Platform.QQ)}
        self.assertNotIn("proxy", sections)

    def test_rendered_config_roundtrips(self) -> None:
        """初值文本落盘后能被 ConfigIO 读回"""
        import tempfile
        from pathlib import Path

        from utils.config._io import ConfigIO
        from utils.config._writer import render_config
        from utils.paths import PLATFORM

        path = Path(tempfile.mkdtemp()) / "config.toml"
        path.write_text(render_config(PLATFORM), encoding="utf-8")
        data = ConfigIO(path).load()
        self.assertIn("chore", data)
        self.assertEqual(data["global"]["network_timeout"], 90.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
