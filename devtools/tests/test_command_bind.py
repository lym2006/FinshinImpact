# devtools/tests/test_command_bind.py
"""命令片段绑定的单元测试

- 覆盖带值开关名单下的绑定形状
- 覆盖缺值、开关紧跟开关与位置参数的先后
- 覆盖清单声明下的开关取值与位置参数落点
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from plugins.help import _commands  # noqa: E402
from core.domain import BoundCommand, bind_command  # noqa: E402
from core.dto import CommandDTO, HelpCommandDTO, HelpFlagDTO  # noqa: E402

_TAKES_VALUE = frozenset({"-t"})


class TestBindCommand(unittest.TestCase):
    """按带值开关名单绑定片段"""

    def test_value_flag_eats_next_piece(self) -> None:
        bound = bind_command(("-t", "5"), _TAKES_VALUE)
        self.assertEqual(bound.flags, (("-t", "5"),))
        self.assertEqual(bound.args, ())

    def test_value_flag_without_next_piece_leaves_empty(self) -> None:
        bound = bind_command(("-t",), _TAKES_VALUE)
        self.assertEqual(bound.flags, (("-t", ""),))

    def test_flag_after_value_flag_stays_a_flag(self) -> None:
        bound = bind_command(("-t", "-h"), _TAKES_VALUE)
        self.assertEqual(bound.flags, (("-t", ""), ("-h", "")))
        self.assertEqual(bound.args, ())

    def test_piece_outside_value_flag_list_is_flag(self) -> None:
        bound = bind_command(("-i", "5"), _TAKES_VALUE)
        self.assertEqual(bound.flags, (("-i", ""),))
        self.assertEqual(bound.args, ("5",))

    def test_pieces_before_flag_keep_order(self) -> None:
        bound = bind_command(("甲", "-t", "5", "乙"), _TAKES_VALUE)
        self.assertEqual(bound.flags, (("-t", "5"),))
        self.assertEqual(bound.args, ("甲", "乙"))

    def test_repeated_value_flag_keeps_each_pair(self) -> None:
        bound = bind_command(("-t", "5", "-t", "6"), _TAKES_VALUE)
        self.assertEqual(bound.flags, (("-t", "5"), ("-t", "6")))

    def test_empty_pieces_bind_empty(self) -> None:
        self.assertEqual(bind_command((), _TAKES_VALUE), BoundCommand())

    def test_value_of_reads_declared_pair(self) -> None:
        bound = bind_command(("-t", "5"), _TAKES_VALUE)
        self.assertEqual(bound.value_of("-t"), "5")
        self.assertEqual(bound.value_of("-i"), "")


class TestBindAgainstSpecs(unittest.TestCase):
    """按清单声明挑出带值开关"""

    def setUp(self) -> None:
        specs = {
            "demo": HelpCommandDTO(
                cmd="demo",
                desc="演示命令",
                flags=(
                    HelpFlagDTO("-i", "不带值的开关"),
                    HelpFlagDTO("-t", "带值的开关", "秒数"),
                ),
                args="要带的内容",
            )
        }
        patcher = patch.object(_commands, "command_specs", specs)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _bound(self, *pieces: str) -> BoundCommand:
        return _commands._bind(CommandDTO(matched=True, head="demo", pieces=pieces))

    def test_declared_value_flag_takes_next_piece(self) -> None:
        self.assertEqual(self._bound("-t", "5", "你好").flags, (("-t", "5"),))

    def test_undeclared_flag_takes_no_value(self) -> None:
        self.assertEqual(self._bound("-i", "5").flags, (("-i", ""),))

    def test_positional_pieces_stay_args(self) -> None:
        self.assertEqual(self._bound("你好", "世界").args, ("你好", "世界"))

    def test_undeclared_command_head_binds_without_value(self) -> None:
        command = CommandDTO(matched=True, head="other", pieces=("-t", "5"))
        self.assertEqual(_commands._bind(command).flags, (("-t", ""),))


if __name__ == "__main__":
    unittest.main()
