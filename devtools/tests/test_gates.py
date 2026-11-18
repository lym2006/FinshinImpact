"""闸门目标发现与步选择的单元测试

- 改名声明那项 package-dir 映射是子仓的唯一认法：没声明的跳过，构建产物里的副本不重算
- 空壳目录与不带映射的声明文件都不进目标，发现结果只由声明决定
- 新挂一只带改名声明的子仓后无需改代码即出现在目标里
- 源码类步的目标含本体三棵树与各子仓源码目录，用例目标只收带用例目录的
- --only 缺省跑齐五步，指定后只跑点名的步，任一步红整体退一
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gates  # noqa: E402

_DECL = """
[project]
name = "{name}"

[tool.setuptools]
package-dir = {{ "{pkg}" = "src" }}
"""

_NO_DECL = """
[project]
name = "{name}"
dependencies = []
"""


def _stage(root: Path) -> None:
    """造一棵假仓根：一只带源码与用例的子仓、一只带声明缺用例目录的、一只空壳、一只插件"""
    tg = root / "finshin" / "adapter" / "tg"
    (tg / "src").mkdir(parents=True)
    (tg / "tests").mkdir()
    (tg / "pyproject.toml").write_text(
        _DECL.format(name="finshin-adapter-tg", pkg="finshin_adapter_tg"),
        encoding="utf-8",
    )
    sdk = root / "finshin" / "sdk"
    (sdk / "src").mkdir(parents=True)
    (sdk / "pyproject.toml").write_text(
        _DECL.format(name="finshin-sdk", pkg="finshin_sdk"), encoding="utf-8"
    )
    (root / "finshin" / "adapter" / "qq").mkdir(parents=True)
    demo = root / "finshin" / "plugin" / "demo"
    demo.mkdir(parents=True)
    (demo / "pyproject.toml").write_text(
        _NO_DECL.format(name="finshin-plugin-demo"), encoding="utf-8"
    )
    copy = root / "finshin" / "sdk" / "build" / "lib"
    copy.mkdir(parents=True)
    (copy / "pyproject.toml").write_text(
        _DECL.format(name="finshin-sdk", pkg="finshin_sdk"), encoding="utf-8"
    )


class TestDiscoverSubrepos(unittest.TestCase):
    """按改名声明发现子仓"""

    def setUp(self) -> None:
        """铺假仓根"""
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = Path(holder.name)
        _stage(self.root)

    def test_only_declared_subrepos_are_found(self) -> None:
        """空壳与不带映射的声明都不进结果，构建副本不重算"""
        found = gates._discover_subrepos(self.root)
        self.assertEqual(
            [(s.rel, s.sources, s.tests) for s in found],
            [
                (
                    "finshin/adapter/tg",
                    ("finshin/adapter/tg/src",),
                    "finshin/adapter/tg/tests",
                ),
                ("finshin/sdk", ("finshin/sdk/src",), None),
            ],
        )

    def test_new_mount_is_found_without_code_change(self) -> None:
        """新挂一只带改名声明的子仓，结果多出它且旧项不动"""
        fresh = self.root / "finshin" / "adapter" / "fs"
        (fresh / "src").mkdir(parents=True)
        (fresh / "pyproject.toml").write_text(
            _DECL.format(name="finshin-adapter-fs", pkg="finshin_adapter_fs"),
            encoding="utf-8",
        )
        found = gates._discover_subrepos(self.root)
        self.assertEqual(len(found), 3)
        self.assertIn("finshin/adapter/fs/src", found[0].sources)

    def test_missing_mount_root_is_empty(self) -> None:
        """装载根没建时发现结果为空表，不报错"""
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.assertEqual(gates._discover_subrepos(Path(holder.name)), ())


class TestGateTargets(unittest.TestCase):
    """步目标的汇总形状"""

    def setUp(self) -> None:
        """铺假仓根"""
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = Path(holder.name)
        _stage(self.root)

    def test_source_targets_cover_main_and_subrepos(self) -> None:
        """源码类步的目标先本体三棵树，再按序补子仓源码目录"""
        self.assertEqual(
            gates._source_targets(self.root),
            (
                "src",
                "packaging",
                "devtools",
                "finshin/adapter/tg/src",
                "finshin/sdk/src",
            ),
        )

    def test_pytest_targets_take_subrepos_with_tests_only(self) -> None:
        """用例目标含本体用例树与带用例目录的子仓，缺用例目录的不进"""
        self.assertEqual(
            gates._pytest_targets(self.root),
            ("devtools/tests", "finshin/adapter/tg/tests"),
        )


class TestOnlySelection(unittest.TestCase):
    """--only 的步选择与退出码"""

    def _green(self, name: str) -> gates._StepResult:
        """记步名并回绿"""
        self.calls.append(name)
        return gates._StepResult(True, "0", "")

    def setUp(self) -> None:
        """准备替身记录"""
        self.calls: list[str] = []

    def test_default_runs_all_steps_in_order(self) -> None:
        """不给 --only 时按定序跑齐五步"""
        code = gates.main([], dispatch=self._green)
        self.assertEqual(self.calls, list(gates._STEPS))
        self.assertEqual(code, 0)

    def test_only_selects_named_steps(self) -> None:
        """点名两步就只跑两步，按点名的先后"""
        code = gates.main(["--only", "pyright", "--only", "ruff"], dispatch=self._green)
        self.assertEqual(self.calls, ["pyright", "ruff"])
        self.assertEqual(code, 0)

    def test_red_step_exits_one(self) -> None:
        """任一步红整体退一，其余步照跑"""

        def dispatch(name: str) -> gates._StepResult:
            result = self._green(name)
            return (
                result
                if name != "imports"
                else gates._StepResult(False, "1", "broken 1")
            )

        self.assertEqual(gates.main([], dispatch=dispatch), 1)
        self.assertEqual(self.calls, list(gates._STEPS))

    def test_default_dispatch_invokes_registry(self) -> None:
        """不给替身时走仓内登记表，登记的函数被真正调用"""
        calls: list[str] = []

        def make(name: str):
            def run() -> gates._StepResult:
                calls.append(name)
                return gates._StepResult(True, "0", "")

            return run

        original = dict(gates._STEP_FUNCS)
        self.addCleanup(gates._STEP_FUNCS.update, original)
        for step in gates._STEPS:
            gates._STEP_FUNCS[step] = make(step)
        self.assertEqual(gates.main([]), 0)
        self.assertEqual(calls, list(gates._STEPS))


if __name__ == "__main__":
    unittest.main()
