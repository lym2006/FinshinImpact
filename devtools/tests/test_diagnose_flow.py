# devtools/tests/test_diagnose_flow.py
"""网络诊断轮测试

- 全挂后复测命中本轮已探测的端点，按瞬时抖动通过且不带断链标记
- 复测命中其他端口，仍判当前配置不通并发断链标记
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

from utils.check import (  # noqa: E402
    TelegramFieldKey,
    _diagnose,
)
from utils.network import FrameKey, RowId, RowStatus  # noqa: E402

_CFG = "http://127.0.0.1:7897"
_ALT = "http://127.0.0.1:7890"
_ALT_PORT_SERVER = "127.0.0.1:7890"


def _probe(passes: Callable[[str, int], bool]):
    """构造按 (地址, 该地址第几次被探) 裁决的探测桩"""
    calls: dict[str, int] = {}

    async def fake(token: str, proxy: str) -> tuple[str | None, dict[str, str]]:
        calls[proxy] = calls.get(proxy, 0) + 1
        if passes(proxy, calls[proxy]):
            return proxy, {}
        return None, {TelegramFieldKey.PROXY: "无法连接到代理服务器"}

    return fake


@contextmanager
def _stubbed_round(cfg: str, registry_server: str, passes: Callable[[str, int], bool]):
    """桩掉网络与引擎后跑一轮诊断，收集进度帧

    - 系统代理按未开启处理，本机端口一律探活
    """
    frames: list[dict] = []
    with (
        patch.object(_diagnose, "attempt_channel", _probe(passes)),
        patch.object(_diagnose, "preload_engine"),
        patch.object(_diagnose, "detect_system_proxy", return_value=None),
        patch.object(
            _diagnose, "registry_proxy", return_value={"server": registry_server}
        ),
        patch.object(_diagnose, "port_alive", return_value=True),
    ):
        yield frames


def _advice(frames: list[dict]) -> dict:
    """取结论行最后一帧"""
    return [f for f in frames if f.get("id") == RowId.ADVICE][-1]


class TestDiagnoseFlow(unittest.IsolatedAsyncioTestCase):
    """全挂后的复测收尾"""

    async def test_retest_same_endpoint_is_flap(self) -> None:
        """配置代理首探失败、复测同端点通过

        - 结论行转绿为抖动，不发断链标记
        """
        with _stubbed_round(_CFG, "", lambda p, n: p == _CFG and n == 2) as frames:
            await _diagnose.diagnose_flow(_CFG, "123:abc", frames.append)

        advice = _advice(frames)
        self.assertEqual(advice["status"], RowStatus.OK)
        self.assertIn("瞬时抖动", advice["detail"])
        self.assertNotIn(FrameKey.BROKEN, advice)

    async def test_retest_other_endpoint_stays_fail(self) -> None:
        """配置代理始终不通、另一个本机端口可出网

        - 结论行报出该地址并保留断链标记
        """
        with _stubbed_round(_CFG, _ALT_PORT_SERVER, lambda p, _: p == _ALT) as frames:
            await _diagnose.diagnose_flow(_CFG, "123:abc", frames.append)

        advice = _advice(frames)
        self.assertEqual(advice["status"], RowStatus.FAIL)
        self.assertIn(_ALT, advice["detail"])
        self.assertTrue(advice.get(FrameKey.BROKEN))

    async def test_channel_rows_keep_first_round_state(self) -> None:
        """抖动收尾不翻案通道行

        - 配置代理与直连保持首探落红，转绿的只有结论行
        """
        with _stubbed_round(_CFG, "", lambda p, n: p == _CFG and n == 2) as frames:
            await _diagnose.diagnose_flow(_CFG, "123:abc", frames.append)

        settled = {
            f["id"]: f["status"]
            for f in frames
            if f.get("id") in (RowId.CFG, RowId.DIRECT)
        }
        self.assertEqual(
            settled, {RowId.CFG: RowStatus.FAIL, RowId.DIRECT: RowStatus.FAIL}
        )


if __name__ == "__main__":
    unittest.main()
