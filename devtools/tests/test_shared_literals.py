"""两侧同值串的钉死用例

- 本体侧与生成侧、启动器侧各写一遍的串，逐样比对
- 目录段名与键位对不上，生成的目录本体读不出
- Pages 地址与镜像名单对不上，取件就取到别处去
- 包内布局名与注册表值名对不上，升级保留与代理读取各说各话
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "packaging"))
sys.path.insert(0, str(ROOT / "packaging" / "launch"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

import gen_catalog  # noqa: E402
import pack_spec  # noqa: E402
import proxy as launch_proxy  # noqa: E402

from services import adapter_catalog as catalog_mod  # noqa: E402
from services.env_setup import toolchain, wheel_fetch  # noqa: E402
from system import (  # noqa: E402
    app_identity,
    links,
    profile_env,
    registry,
    tool_settings,
)

_WORKFLOW = ROOT / ".github" / "workflows" / "static.yml"


class TestCatalogShape(unittest.TestCase):
    """目录文本的段名与键位"""

    def test_sections_match_generator(self) -> None:
        """段名两处同值，改一处即读不出"""
        self.assertEqual(catalog_mod._SECTION_SDK, gen_catalog._SECTION_SDK)
        self.assertEqual(catalog_mod._SECTION_ADAPTER, gen_catalog._SECTION_ADAPTER)

    def test_keys_match_generator(self) -> None:
        """键位两处同值，改一处即读不出"""
        self.assertEqual(
            {str(key) for key in catalog_mod._RowKey},
            {
                gen_catalog._KEY_PLATFORM,
                gen_catalog._KEY_DISTRIBUTION,
                gen_catalog._KEY_VERSION,
                gen_catalog._KEY_URL,
                gen_catalog._KEY_SHA256,
            },
        )

    def test_wheel_suffix_matches_generator(self) -> None:
        """wheel 附件名后缀两处同值"""
        self.assertEqual(wheel_fetch._WHEEL_SUFFIX, gen_catalog._WHEEL_SUFFIX)

    def test_catalog_path_matches_workflow(self) -> None:
        """本体读的目录文件名与工作流部署的那个同名"""
        deployed = [
            line.strip()
            for line in _WORKFLOW.read_text(encoding="utf-8").splitlines()
            if "site/adapters" in line
        ]
        self.assertEqual(len(deployed), 1, deployed)
        tail = links.CATALOG_PATH.rpartition("/")[2]
        self.assertIn(f"site/{tail}", deployed[0])


class TestEndpoints(unittest.TestCase):
    """取数地址"""

    def test_pages_host_matches_launcher(self) -> None:
        """版本页与在线目录同主机，本体与启动器各写一遍"""
        self.assertTrue(pack_spec._PAGES_PYPROJECT_URL.startswith(links.PAGES_BASE_URL))

    def test_api_host_matches_generator(self) -> None:
        """发布接口主机名本体与生成侧同值"""
        self.assertEqual(pack_spec.API_HOST, links.API_BASE_URL)

    def test_mirrors_come_from_the_setting_table(self) -> None:
        """镜像名单只有配置表一个出处"""
        self.assertEqual(
            tuple(toolchain.GITHUB_MIRRORS), tuple(pack_spec.release_mirrors())
        )


class TestNaming(unittest.TestCase):
    """分发名与包内目录名"""

    def test_distribution_names_match_dev_sources(self) -> None:
        """生成侧认的那两个分发名与开发工具清单里的本地源码同名"""
        sources = _read_uv_sources()
        self.assertIn(gen_catalog._SDK_DISTRIBUTION, sources)
        others = {name for name in sources if name != gen_catalog._SDK_DISTRIBUTION}
        self.assertTrue(
            all(name.startswith(gen_catalog._ADAPTER_PREFIX) for name in others)
        )

    def test_runtime_dir_name_matches_toolchain(self) -> None:
        """包内运行目录名启动器与本体同值"""
        self.assertEqual(toolchain.RUNTIME_DIR.name, pack_spec.PackLayout.RUNTIME_DIR)

    def test_interpreter_names_match_toolchain(self) -> None:
        """包内解释器名启动器与本体同值"""
        self.assertEqual(toolchain._PY_EXE.name, pack_spec.PackLayout.PYTHON_EXE)

    def test_declaration_name_matches_packaging(self) -> None:
        """项目声明文件名本体两份与启动器同值"""
        self.assertEqual(
            profile_env.DECLARATION_FILE_NAME, pack_spec.PackLayout.DECLARATION
        )
        self.assertEqual(
            tool_settings._ROOT_DECLARATION.name, profile_env.DECLARATION_FILE_NAME
        )
        self.assertEqual(
            tool_settings.DEVTOOLS_DECLARATION.name, profile_env.DECLARATION_FILE_NAME
        )

    def test_icon_name_matches_build(self) -> None:
        """图标文件名本体与构建侧同值"""
        self.assertEqual(app_identity.APP_ICON_PATH.name, pack_spec.PackLayout.ICON)


class TestRegistryNames(unittest.TestCase):
    """注册表值名"""

    def test_proxy_value_names_match_launcher(self) -> None:
        """代理开关与代理地址两个值名本体与启动器同值"""
        self.assertEqual(registry._PROXY_ENABLE_VALUE, launch_proxy._PROXY_ENABLE_VALUE)
        self.assertEqual(registry._PROXY_SERVER_VALUE, launch_proxy._PROXY_SERVER_VALUE)


def _read_uv_sources() -> set[str]:
    """取开发工具清单里的本地源码分发名"""
    import tomllib

    data = tomllib.loads(
        (ROOT / "devtools" / "pyproject.toml").read_text(encoding="utf-8")
    )
    return set(data.get("tool", {}).get("uv", {}).get("sources", {}))


if __name__ == "__main__":
    unittest.main()
