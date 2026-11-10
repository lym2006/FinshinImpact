# src/adapters/telegram/diagnose.py
"""网络连通诊断

- 按代理模式只测选定路线
- 全部通道失败给不通结论并标记断链
"""

import time
from collections.abc import Awaitable, Callable, Sequence

from finshin_sdk.domain import ProxyMode
from skin.messages import CheckMessage
from utils.check import run_probe_round
from utils.logger import get_logger
from utils.network import (
    Channel,
    FrameKey,
    RowId,
    RowStatus,
    detect_system_proxy,
    via_label,
)
from utils.network.probe import (
    plan_channels,
    single_row_of,
    sys_deduped,
    verify_plan,
)

from .probe import attempt_channel, preload_engine

# 诊断跑在后台线程的私有 loop，计时句走此器落 debug
_logger = get_logger("Mgr.Diagnose")


def _never_stop() -> bool:
    """默认停止回调"""
    return False


def _never_emit(_frame_data: dict) -> None:
    """无回调占位"""
    return None


def _opening(
    channels: Sequence[Channel],
    configured: str,
    detected: str | None,
    single: tuple[str, str, str] | None,
    head: str = "",
) -> dict:
    """组装诊断整表帧

    - 带头部文案时一并给出弹窗提示
    """
    frame: dict = {
        FrameKey.ROWS: verify_plan(
            channels, sys_dedup=sys_deduped(configured, detected), single=single
        )
    }
    if head:
        frame[FrameKey.HEAD] = head
    return frame


def _diagnose_probe(
    token: str,
) -> Callable[[Channel], Awaitable[tuple[str | None, dict[str, str], str]]]:
    """构造诊断探针

    - 用真实凭证探测
    """

    async def probe(ch: Channel) -> tuple[str | None, dict[str, str], str]:
        start = time.monotonic()
        resolved, errors = await attempt_channel(token, ch.url)
        _logger.debug(
            CheckMessage.COST.format(via=via_label(ch), cost=time.monotonic() - start)
        )

        # 表格句留空由核心统一拼"称谓：可达/不可用"
        return resolved, errors, ""

    return probe


async def diagnose_flow(
    configured_proxy: str = "",
    token: str = "",
    mode: str = ProxyMode.AUTO,
    emit: Callable[[dict], None] | None = None,
    stop_check: Callable[[], bool] | None = None,
) -> None:
    """执行一轮网络诊断

    - 只测本模式用得到的路线，缺席不发探测
    - 两轮都全挂才定不通，给不通结论并标记断链
    - 收到中止请求时取消在测任务，不输出结论
    """
    frame = emit or _never_emit
    stop = stop_check or _never_stop

    detected = detect_system_proxy()
    cfg = configured_proxy.strip()
    channels = plan_channels(cfg, detected, mode=mode)
    single = single_row_of(mode)

    # 首帧把通道行点亮为检测中即启动界面倒计时，引擎导入费须在这之前付完
    preload_engine()
    frame(_opening(channels, cfg, detected, single))

    def replay() -> None:
        """预热后重发整表清场"""
        _logger.debug(CheckMessage.RETRY_HEAD)
        frame(_opening(channels, cfg, detected, single, head=CheckMessage.RETRY_HEAD))

    outcome = await run_probe_round(
        channels, _diagnose_probe(token), frame, via_label, replay, stop
    )
    if stop():
        return

    if outcome.passed:
        frame(
            {
                "id": RowId.ADVICE,
                "status": RowStatus.OK,
                "detail": CheckMessage.ADVICE_OK,
            }
        )
        return

    frame(
        {
            "id": RowId.ADVICE,
            "status": RowStatus.FAIL,
            "detail": CheckMessage.DIAG_ADVICE_NONE,
            FrameKey.BROKEN: True,
        }
    )
