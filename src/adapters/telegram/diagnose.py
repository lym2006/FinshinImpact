# src/adapters/telegram/diagnose.py
"""网络连通诊断

- 按代理模式只测选定路线，缺席行首帧直接给结论
- 全部通道失败给不通结论并标记断链
"""

import time
from collections.abc import Awaitable, Callable, Sequence

from core.domain import ProxyMode
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
    probe_budget,
    single_row_of,
    sys_deduped,
)

from .probe import attempt_channel, preload_engine

# 诊断跑在后台线程的私有 loop，计时句走此器落 debug
_logger = get_logger("Mgr.Diagnose")

# 固定骨架：id 与标题（界面与生成器共用，顺序即阶梯优先级），本地配置行只属校验轮
_ROWS = (
    (RowId.CFG, CheckMessage.ROW_CFG),
    (RowId.SYS, CheckMessage.ROW_SYS),
    (RowId.DIRECT, CheckMessage.ROW_DIRECT),
    (RowId.ADVICE, CheckMessage.ROW_ADVICE),
)


def _never_stop() -> bool:
    """默认停止回调"""
    # 永不中断
    return False


def _never_emit(_frame_data: dict) -> None:
    """无回调占位"""
    # 独立调用时静默消费帧
    return None


def _diagnose_plan(
    channels: Sequence[Channel],
    sys_dedup: bool = False,
    single: tuple[str, str, str] | None = None,
) -> list[dict]:
    """生成诊断首帧整表

    - 待探测通道标进行中，缺席行直接给结论
    - sys_dedup 为真时系统代理行标同端点去重而非缺席
    - single 传入即单路模式，表裁成选定通道行加结论行
    """
    present = {ch.kind for ch in channels}
    budgets = {ch.kind: probe_budget(ch.url) for ch in channels}
    absent = {
        RowId.CFG: (RowStatus.FAIL, CheckMessage.CFG_EMPTY),
        RowId.SYS: (RowStatus.FAIL, CheckMessage.SYS_UNAVAILABLE),
    }
    rows: list[dict] = []
    for rid, title in _ROWS:
        if single is not None and rid not in (single[0], RowId.ADVICE):
            continue
        if rid in present:
            status, detail = RowStatus.CHECKING, ""
        elif single is not None and rid == single[0]:
            status, detail = RowStatus.FAIL, single[2]
        elif rid == RowId.SYS and sys_dedup:
            status, detail = RowStatus.SKIP, CheckMessage.SYS_DEDUP
        elif rid in absent:
            status, detail = absent[rid]
        else:
            status, detail = RowStatus.PENDING, ""
        row = {"id": rid, "title": title, "status": status, "detail": detail}
        if rid in budgets:
            row["budget"] = str(int(budgets[rid]))
        rows.append(row)
    return rows


def _opening(
    channels: Sequence[Channel],
    configured: str,
    detected: str | None,
    single: tuple[str, str, str] | None,
    head: str = "",
) -> dict:
    """组装诊断整表帧

    - head 非空即同时给出弹窗头部提示
    """
    frame: dict = {
        FrameKey.ROWS: _diagnose_plan(
            channels, sys_deduped(configured, detected), single
        )
    }
    if head:
        frame[FrameKey.HEAD] = head
    return frame


def _diagnose_probe(
    token: str,
) -> Callable[[Channel], Awaitable[tuple[str | None, dict[str, str], str]]]:
    """构造诊断探针

    - 与校验轮同走 attempt_channel，用真实 token 探测
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
    - 任一通道可用即通过，两轮都全挂才定不通
    - 全挂给不通结论并标记断链
    - stop_check 为真时中止并取消在测任务，不输出结论
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
