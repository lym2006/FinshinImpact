# devtools/tests/test_diagnose_flow.py
"""网络诊断轮测试

- 任一通道可达给通过结论且不带断链标记
- 全部通道失败给不通结论并标记断链
- 缺席通道在首帧整表给结论，不发探测
"""

import sys
import unittest
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from system.profile_env import set_profile  # noqa: E402

set_profile("tg.000000")

from adapters.telegram import diagnose as diagnose_mod  # noqa: E402
from core.domain import FieldKey  # noqa: E402
from utils.network import FrameKey, RowId, RowStatus  # noqa: E402

_CFG = "http://127.0.0.1:7897"


@contextmanager
def _stubbed_round(cfg: str, passes: Callable[[str], bool]):
    """桩掉网络与引擎后跑一轮诊断，收集进度帧与被探地址

    - 系统代理按未开启处理
    - passes 按代理地址裁决该通道是否可出网
    """
    frames: list[dict] = []
    seen: list[str] = []

    async def fake(token: str, proxy: str) -> tuple[str | None, dict[str, str]]:
        seen.append(proxy)
        if passes(proxy):
            return proxy, {}
        return None, {FieldKey.PROXY: "无法连接到代理服务器"}

    with (
        patch.object(diagnose_mod, "attempt_channel", fake),
        patch.object(diagnose_mod, "preload_engine"),
        patch.object(diagnose_mod, "detect_system_proxy", return_value=None),
    ):
        yield frames, seen


def _advice(frames: list[dict]) -> dict:
    """取结论行最后一帧"""
    return [f for f in frames if f.get("id") == RowId.ADVICE][-1]


def _opening_rows(frames: list[dict]) -> dict[str, dict]:
    """取首帧整表并按行 id 索引"""
    table = [f for f in frames if FrameKey.ROWS in f][0]
    return {r["id"]: r for r in table[FrameKey.ROWS]}


class TestDiagnoseFlow(unittest.IsolatedAsyncioTestCase):
    """通道阶梯的收尾结论"""

    async def test_all_channels_fail_marks_broken(self) -> None:
        """配置代理与直连均不通

        - 结论行报未找到可用通道并带断链标记
        """
        with _stubbed_round(_CFG, lambda p: False) as (frames, seen):
            await diagnose_mod.diagnose_flow(_CFG, "123:abc", frames.append)

        advice = _advice(frames)
        self.assertEqual(advice["status"], RowStatus.FAIL)
        self.assertIn("未找到可用通道", advice["detail"])
        self.assertTrue(advice.get(FrameKey.BROKEN))
        self.assertCountEqual(seen, [_CFG, ""], "配置代理与直连两路都该探到")

    async def test_config_channel_alive_settles_ok(self) -> None:
        """配置代理可出网

        - 结论行转绿且不发断链标记
        """
        with _stubbed_round(_CFG, lambda p: p == _CFG) as (frames, _seen):
            await diagnose_mod.diagnose_flow(_CFG, "123:abc", frames.append)

        advice = _advice(frames)
        self.assertEqual(advice["status"], RowStatus.OK)
        self.assertNotIn(FrameKey.BROKEN, advice)

    async def test_absent_config_row_settles_in_opening(self) -> None:
        """配置代理留空

        - 首帧把配置行标为未配置
        - 只探直连一路
        """
        with _stubbed_round("", lambda p: False) as (frames, seen):
            await diagnose_mod.diagnose_flow("", "123:abc", frames.append)

        rows = _opening_rows(frames)
        self.assertEqual(rows[RowId.CFG]["status"], RowStatus.FAIL)
        self.assertIn("未配置", rows[RowId.CFG]["detail"])
        self.assertEqual(seen, [""], "缺席的代理项不该发探测")


if __name__ == "__main__":
    unittest.main()
