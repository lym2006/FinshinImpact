# devtools/tests/test_diagnose_flow.py
"""网络诊断轮测试

- 按代理模式只测选定路线，缺席通道在首帧整表给结论
- 任一通道可达给通过结论且不带断链标记
- 全部通道失败给不通结论并标记断链
- 首轮全挂预热后重跑一轮，两轮都全挂才定性
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
from core.domain import FieldKey, ProxyMode  # noqa: E402
from skin.messages import CheckMessage  # noqa: E402
from utils.check import _verify as verify_mod  # noqa: E402
from utils.network import FrameKey, RowId, RowStatus  # noqa: E402

_CFG = "http://127.0.0.1:7897"
_SYS = "http://127.0.0.1:7890"


@contextmanager
def _stubbed_round(
    cfg: str,
    passes: Callable[[str], bool],
    sys_proxy: str | None = None,
    max_probes: int | None = None,
):
    """桩掉网络与引擎后跑一轮诊断，收集进度帧与被探地址

    - passes 按代理地址裁决该通道是否可出网
    - max_probes 限死总探测次数，超出即断言失败
    """
    frames: list[dict] = []
    seen: list[str] = []

    async def fake(token: str, proxy: str) -> tuple[str | None, dict[str, str]]:
        seen.append(proxy)
        if max_probes is not None and len(seen) > max_probes:
            raise AssertionError("探测次数超出预期")
        if passes(proxy):
            return proxy, {}
        return None, {FieldKey.PROXY: "无法连接到代理服务器"}

    with (
        patch.object(diagnose_mod, "attempt_channel", fake),
        patch.object(diagnose_mod, "preload_engine"),
        patch.object(diagnose_mod, "detect_system_proxy", lambda: sys_proxy),
        patch.object(verify_mod, "_RETRY_WARMUP", 0.0),
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

        - 两轮都全挂才给结论，结论行报未找到可用通道并带断链标记
        """
        with _stubbed_round(_CFG, lambda p: False) as (frames, seen):
            await diagnose_mod.diagnose_flow(
                _CFG, "123:abc", ProxyMode.AUTO, frames.append
            )

        advice = _advice(frames)
        self.assertEqual(advice["status"], RowStatus.FAIL)
        self.assertIn("未找到可用通道", advice["detail"])
        self.assertTrue(advice.get(FrameKey.BROKEN))
        self.assertEqual(seen, [_CFG, "", _CFG, ""], "两轮都该探配置与直连")

    async def test_config_channel_alive_settles_ok(self) -> None:
        """配置代理可出网

        - 结论行转绿且不发断链标记
        """
        with _stubbed_round(_CFG, lambda p: p == _CFG) as (frames, _seen):
            await diagnose_mod.diagnose_flow(
                _CFG, "123:abc", ProxyMode.AUTO, frames.append
            )

        advice = _advice(frames)
        self.assertEqual(advice["status"], RowStatus.OK)
        self.assertNotIn(FrameKey.BROKEN, advice)

    async def test_absent_config_row_settles_in_opening(self) -> None:
        """配置代理留空

        - 首帧把配置行标为未配置
        - 缺席行不发探测，直连两轮各探一次
        """
        with _stubbed_round("", lambda p: False) as (frames, seen):
            await diagnose_mod.diagnose_flow(
                "", "123:abc", ProxyMode.AUTO, frames.append
            )

        rows = _opening_rows(frames)
        self.assertEqual(rows[RowId.CFG]["status"], RowStatus.FAIL)
        self.assertIn("未配置", rows[RowId.CFG]["detail"])
        self.assertEqual(seen, ["", ""], "缺席的代理项不该发探测")

    async def test_retry_head_replays_whole_table(self) -> None:
        """预热重跑前重发整表

        - 第二张整表带重测头部提示
        """
        with _stubbed_round(_CFG, lambda p: False) as (frames, _seen):
            await diagnose_mod.diagnose_flow(
                _CFG, "123:abc", ProxyMode.AUTO, frames.append
            )

        tables = [f for f in frames if FrameKey.ROWS in f]
        self.assertEqual(len(tables), 2)
        self.assertEqual(tables[1].get(FrameKey.HEAD), CheckMessage.RETRY_HEAD)


class TestDiagnoseHonoursMode(unittest.IsolatedAsyncioTestCase):
    """诊断轮认代理模式，与校验轮同走一张路线表"""

    async def test_sys_mode_probes_only_system_route(self) -> None:
        """仅系统代理档不探配置与直连

        - 整表裁成系统代理行与结论行两行
        """
        with _stubbed_round(_CFG, lambda p: False, sys_proxy=_SYS, max_probes=4) as (
            frames,
            seen,
        ):
            await diagnose_mod.diagnose_flow(
                _CFG, "123:abc", ProxyMode.SYS, frames.append
            )

        self.assertEqual(seen, [_SYS, _SYS], "只该反复探系统代理一路")
        self.assertEqual(set(_opening_rows(frames)), {RowId.SYS, RowId.ADVICE})

    async def test_direct_mode_ignores_configured_proxy(self) -> None:
        """仅直连档带着代理地址也只探直连"""
        with _stubbed_round(_CFG, lambda p: not p, max_probes=2) as (frames, seen):
            await diagnose_mod.diagnose_flow(
                _CFG, "123:abc", ProxyMode.DIRECT, frames.append
            )

        self.assertEqual(seen, [""], "配置代理那一档不该被探")
        self.assertEqual(set(_opening_rows(frames)), {RowId.DIRECT, RowId.ADVICE})
        self.assertEqual(_advice(frames)["status"], RowStatus.OK)

    async def test_cfg_mode_absent_settles_without_probe(self) -> None:
        """仅配置代理档留空即缺席

        - 首帧给缺席结论，一个探测包都不发
        """
        with _stubbed_round("", lambda p: True) as (frames, seen):
            await diagnose_mod.diagnose_flow(
                "", "123:abc", ProxyMode.CFG, frames.append
            )

        self.assertEqual(seen, [], "缺席的选路不该发探测")
        rows = _opening_rows(frames)
        self.assertEqual(rows[RowId.CFG]["status"], RowStatus.FAIL)
        self.assertIn("代理项为空", rows[RowId.CFG]["detail"])

    async def test_sys_mode_absent_marks_system_row(self) -> None:
        """仅系统代理档没开系统代理时红在系统行"""
        with _stubbed_round(_CFG, lambda p: True) as (frames, seen):
            await diagnose_mod.diagnose_flow(
                _CFG, "123:abc", ProxyMode.SYS, frames.append
            )

        self.assertEqual(seen, [])
        rows = _opening_rows(frames)
        self.assertEqual(rows[RowId.SYS]["status"], RowStatus.FAIL)
        self.assertIn("系统代理未开启", rows[RowId.SYS]["detail"])


if __name__ == "__main__":
    unittest.main()
