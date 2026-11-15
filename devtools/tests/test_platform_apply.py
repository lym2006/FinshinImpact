"""平台组件装卸动作的单元测试

- 卸一只适配器只动它自己与只有它声明过的库
- 卸之前先数这一平台还剩几个实例，认不出平台的目录不算
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from finshin_sdk.domain import Platform  # noqa: E402
from services.adapter_manifest import InstalledAdapter  # noqa: E402
from services.env_setup import platform_apply as mod  # noqa: E402

_ADAPTER = "finshin-adapter-tg"


def _adapter(version: str) -> InstalledAdapter:
    """一只已装的 Telegram 适配器包"""
    return InstalledAdapter(
        platform=Platform.TELEGRAM,
        distribution=_ADAPTER,
        version=version,
        requires=("aiogram==3.29.1", "finshin-sdk>=0.1.0"),
        entry="finshin_adapter_tg.entry",
    )


class TestUninstallNames(unittest.TestCase):
    """卸一只适配器要动的发行件名"""

    def test_only_its_own_libraries(self) -> None:
        """适配器包自身与只有它声明过的库进名单"""
        with (
            patch.object(mod, "installed_adapters", lambda: (_adapter("0.1.0"),)),
            patch.object(
                mod, "keep_union", lambda exclude=None: ["finshin-sdk==0.1.0", "pillow"]
            ),
        ):
            self.assertEqual(
                mod.uninstall_names(str(Platform.TELEGRAM)),
                (_ADAPTER, "aiogram"),
            )

    def test_absent_adapter_names_nothing(self) -> None:
        """本机没装那只包即一个名字都不交"""
        with patch.object(mod, "installed_adapters", lambda: ()):
            self.assertEqual(mod.uninstall_names(str(Platform.TELEGRAM)), ())


class TestInstancesOf(unittest.TestCase):
    """卸适配器前先查的实例数"""

    def test_counts_only_that_platform(self) -> None:
        """只数这一平台的实例，认不出平台的目录不算"""
        profiles = [("tg.1", ""), ("tg.2", ""), ("qq.3", ""), ("别的", "")]
        with patch.object(mod, "list_profiles", lambda: profiles):
            self.assertEqual(mod.instances_of("tg"), 2)
            self.assertEqual(mod.instances_of("qq"), 1)


if __name__ == "__main__":
    unittest.main()
