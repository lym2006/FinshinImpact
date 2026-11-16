"""两侧同值串的钉死用例

- 本体侧与生成侧、启动器侧各写一遍的串，逐样比对
- 目录段名与键位对不上，生成的目录本体读不出
- Pages 地址与镜像名单对不上，取件就取到别处去
- 包内布局名与注册表值名对不上，升级保留与代理读取各说各话
- 注释点名「两处同值」的串逐条比对，改了另一侧没改这侧即红
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
import gen_release  # noqa: E402
import instancelock as launch_instancelock  # noqa: E402
import pack_seed  # noqa: E402
import pack_spec  # noqa: E402
import proxy as launch_proxy  # noqa: E402

from services import adapter_catalog as catalog_mod  # noqa: E402
from services.env_setup import platform_rows, toolchain, wheel_fetch  # noqa: E402
from system import (  # noqa: E402
    app_identity,
    distributions,
    instance_lock,
    links,
    proc,
    profile_env,
    registry,
    tool_settings,
)
from utils import paths  # noqa: E402

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
                gen_release.KEY_PLATFORM,
                gen_release.KEY_DISTRIBUTION,
                gen_release.KEY_VERSION,
                gen_release.KEY_URL,
                gen_release.KEY_SHA256,
                gen_release.KEY_VERSIONS,
            },
        )

    def test_wheel_suffix_matches_generator(self) -> None:
        """wheel 附件名后缀两处同值"""
        self.assertEqual(wheel_fetch._WHEEL_SUFFIX, gen_release._WHEEL_SUFFIX)

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


class TestSameValuePairs(unittest.TestCase):
    """注释点名同值的串逐条比对"""

    def test_sdk_tree_dir_matches_build(self) -> None:
        """接口包源码目录本体读的那份与构建侧打 wheel 的那份同处"""
        self.assertEqual(
            Path(platform_rows._SDK_TREE_DIR),
            pack_seed._SDK_SOURCE.relative_to(pack_seed.ROOT),
        )

    def test_bootstrap_mutex_matches_launcher(self) -> None:
        """引导锁名本体与启动器同串，不同名即两个进程各探各的锁"""
        self.assertEqual(
            instance_lock._BOOTSTRAP_MUTEX_NAME,
            launch_instancelock._BOOTSTRAP_MUTEX_NAME,
        )

    def test_aumid_anchor_var_matches_packaging(self) -> None:
        """任务栏身份锚定的环境变量名本体与启动器同串"""
        self.assertEqual(app_identity._AUMID_ANCHOR_VAR, pack_spec.AUMID_ANCHOR_VAR)

    def test_create_no_window_matches_packaging(self) -> None:
        """后台命令不弹窗口那个标志两侧同一个数"""
        self.assertEqual(proc._CREATE_NO_WINDOW, pack_spec.CREATE_NO_WINDOW)

    def test_sdk_distribution_matches_generator(self) -> None:
        """接口包分发名本体与目录生成侧同串"""
        self.assertEqual(distributions.SDK_DISTRIBUTION, gen_release.SDK_DISTRIBUTION)

    def test_persona_placeholder_is_in_the_template(self) -> None:
        """人设模板里写的那个占位符与注入读的那份同串"""
        text = paths.PERSONA_TEMPLATE.read_text(encoding="utf-8")
        self.assertIn(profile_env.OWNER_PLACEHOLDER, text)


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
        self.assertIn(gen_release.SDK_DISTRIBUTION, sources)
        others = {name for name in sources if name != gen_release.SDK_DISTRIBUTION}
        self.assertTrue(
            all(name.startswith(gen_release._ADAPTER_PREFIX) for name in others)
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
