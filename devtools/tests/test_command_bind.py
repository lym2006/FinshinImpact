"""命令片段绑定的单元测试

- 覆盖开关吃值、默认值落位与按默认值类型转换
- 覆盖缺值、未登记开关、重复开关与开关之后出现裸段
- 覆盖清单声明下的位置参数落点与开关顺序
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from bundled.help import _commands  # noqa: E402
from finshin_sdk.domain import BindFailure, BoundCommand, bind_command  # noqa: E402
from finshin_sdk.dto import CommandDTO, HelpCommandDTO, HelpFlagDTO  # noqa: E402

# 一只纯开关与一只整数开关，与清单声明项同形
_FLAGS = (("-i", None), ("-t", 0.0))


class TestBindCommand(unittest.TestCase):
    """按清单声明绑定片段"""

    def _bound(self, *pieces: str, takes_args: bool = False) -> BoundCommand:
        bound = bind_command(pieces, _FLAGS, takes_args)
        assert isinstance(bound, BoundCommand)
        return bound

    def test_absent_flags_fall_on_defaults(self) -> None:
        self.assertEqual(dict(self._bound().flags), {"-i": False, "-t": 0.0})

    def test_value_flag_converts_to_default_type(self) -> None:
        self.assertEqual(dict(self._bound("-t", "5").flags)["-t"], 5.0)

    def test_pure_flag_turns_true_when_present(self) -> None:
        self.assertEqual(dict(self._bound("-i").flags)["-i"], True)

    def test_help_flag_is_always_accepted(self) -> None:
        self.assertIs(dict(self._bound("-h").flags)["-h"], True)

    def test_flag_order_follows_manifest(self) -> None:
        self.assertEqual([name for name, _ in self._bound("-i").flags], ["-i", "-t"])

    def test_pieces_before_first_flag_stay_args(self) -> None:
        bound = self._bound("甲", "乙", "-t", "5", takes_args=True)
        self.assertEqual(bound.args, ("甲", "乙"))
        self.assertEqual(dict(bound.flags)["-t"], 5.0)

    def test_int_flag_keeps_integer_value(self) -> None:
        bound = bind_command(("-n", "3"), (("-n", 1),), False)
        assert isinstance(bound, BoundCommand)
        self.assertEqual(dict(bound.flags)["-n"], 3)

    def test_int_flag_rejects_decimal_input(self) -> None:
        self.assertIsInstance(
            bind_command(("-n", "2.5"), (("-n", 1),), False), BindFailure
        )

    def test_decimal_input_passes_float_flag(self) -> None:
        self.assertEqual(dict(self._bound("-t", "2.5").flags)["-t"], 2.5)

    def test_missing_value_fails(self) -> None:
        for pieces in (("-t",), ("-t", "-i"), ("-t", "-h")):
            with self.subTest(pieces=pieces):
                self.assertIsInstance(bind_command(pieces, _FLAGS, False), BindFailure)

    def test_undeclared_flag_fails(self) -> None:
        self.assertIsInstance(bind_command(("-v", "5"), _FLAGS, False), BindFailure)

    def test_repeated_flag_fails(self) -> None:
        self.assertIsInstance(
            bind_command(("-t", "5", "-t", "6"), _FLAGS, False), BindFailure
        )

    def test_value_out_of_default_type_fails(self) -> None:
        for pieces in (("-t", "甲"), ("-t", "十五")):
            with self.subTest(pieces=pieces):
                self.assertIsInstance(bind_command(pieces, _FLAGS, False), BindFailure)

    def test_piece_after_flag_fails(self) -> None:
        self.assertIsInstance(
            bind_command(("-t", "5", "甲"), _FLAGS, True), BindFailure
        )

    def test_arg_without_declaration_fails(self) -> None:
        self.assertIsInstance(bind_command(("甲",), _FLAGS, False), BindFailure)


class TestBindAgainstSpecs(unittest.TestCase):
    """帮助插件按这条命令的清单声明绑定"""

    def setUp(self) -> None:
        specs = {
            "demo": HelpCommandDTO(
                cmd="demo",
                desc="演示命令",
                flags=(
                    HelpFlagDTO("-i", "不带值的开关"),
                    HelpFlagDTO("-t", "带值的开关", 0.0),
                ),
                args="要带的内容",
            )
        }
        patcher = patch.object(_commands, "command_specs", specs)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _values(self, *pieces: str) -> dict[str, object]:
        bound = _commands._bind(CommandDTO(matched=True, head="demo", pieces=pieces))
        assert isinstance(bound, BoundCommand)
        return dict(bound.flags)

    def test_args_come_before_declared_flags(self) -> None:
        bound = _commands._bind(
            CommandDTO(matched=True, head="demo", pieces=("你好", "-t", "5"))
        )
        assert isinstance(bound, BoundCommand)
        self.assertEqual(bound.args, ("你好",))
        self.assertEqual(self._values("你好", "-t", "5"), {"-i": False, "-t": 5.0})

    def test_value_flag_with_help_keeps_both(self) -> None:
        values = self._values("-t", "5", "-h")
        self.assertEqual((values["-t"], values["-h"]), (5.0, True))

    def test_undeclared_head_fails(self) -> None:
        command = CommandDTO(matched=True, head="other", pieces=("-t", "5"))
        self.assertIsInstance(_commands._bind(command), BindFailure)


if __name__ == "__main__":
    unittest.main()
