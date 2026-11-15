"""项目声明读取件的单元测试

- 根声明与开发工具清单读得到才谈得上装库
- 配置表缺键必须当场报错，代码不许留第二份默认值
- 镜像名单只认 https 前缀，尾巴带斜杠才能直接接地址
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system import tool_settings  # noqa: E402
from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")


class TestDeclaration(unittest.TestCase):
    """两份声明的解析"""

    def test_root_declaration_has_identity(self) -> None:
        """根声明交出项目名与版本号"""
        self.assertEqual(tool_settings.project_value("name"), "finshin-impact")
        self.assertTrue(tool_settings.project_value("version"))

    def test_devtools_declaration_has_pins(self) -> None:
        """开发工具清单交出钉了版本的条目"""
        data = tool_settings.declaration(tool_settings.DEVTOOLS_DECLARATION)
        pins = data.get("project", {}).get("dependencies", [])
        self.assertTrue([pin for pin in pins if "==" in str(pin)])

    def test_missing_key_raises(self) -> None:
        """配置表缺键即报错，不静默回默认值"""
        with self.assertRaises(RuntimeError) as caught:
            tool_settings.tool_setting("no-such-key")
        self.assertIn("no-such-key", str(caught.exception))

    def test_github_mirrors_shape(self) -> None:
        """镜像序列每项都能直接接在地址前面"""
        mirrors = tool_settings.tool_setting("github-mirrors")
        self.assertTrue(mirrors)
        for mirror in mirrors:
            self.assertTrue(str(mirror).startswith("https://"))
            self.assertTrue(str(mirror).endswith("/"))


if __name__ == "__main__":
    unittest.main()
