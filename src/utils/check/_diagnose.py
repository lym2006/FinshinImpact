# src/utils/check/_diagnose.py
"""网络连通诊断

- 配置留空或系统代理未开启的通道，首帧直接给结论
- 全部通道失败时复测本机代理端口，输出结论行
"""

import asyncio
import time
from collections.abc import Awaitable, Callable, Sequence

from skin.messages import CheckMessage

from ..logger import get_logger
from ..network import (
    Channel,
    FrameKey,
    RowId,
    RowStatus,
    detect_system_proxy,
    via_label,
)
from ..network.probe import (
    extract_port,
    is_flap_hit,
    plan_channels,
    port_alive,
    probe_budget,
    sys_deduped,
)
from ..network.proxy import registry_proxy
from ._connectivity import attempt_channel, preload_engine
from ._fields import TelegramFieldKey
from ._verify import run_channels

# 诊断跑在后台线程的私有 loop，计时句走此器落 debug
_logger = get_logger("Mgr.Diagnose")

# 仅当配置项与系统注册表都拿不到端口时，才回退扫描这组常见默认值
_FALLBACK_PORTS = (7890, 7897, 7898)

# 结论行最多复测几个存活端口，防全挂场景等待过长
_ALT_RETEST_LIMIT = 3

# 固定骨架：id 与标题（界面与生成器共用，顺序即阶梯优先级），本地配置行只属校验轮
_ROWS = (
    (RowId.CFG, CheckMessage.ROW_CFG),
    (RowId.SYS, CheckMessage.ROW_SYS),
    (RowId.DIRECT, CheckMessage.ROW_DIRECT),
    (RowId.PORT, CheckMessage.ROW_PORT),
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


def _diagnose_plan(channels: Sequence[Channel], sys_dedup: bool = False) -> list[dict]:
    """生成诊断首帧整表

    - 待探测通道标进行中，缺席行直接给结论
    - sys_dedup 为真时系统代理行标同端点去重而非缺席
    """
    present = {ch.kind for ch in channels}
    budgets = {ch.kind: probe_budget(ch.url) for ch in channels}
    absent = {
        RowId.CFG: (RowStatus.FAIL, CheckMessage.CFG_EMPTY),
        RowId.SYS: (RowStatus.FAIL, CheckMessage.SYS_UNAVAILABLE),
    }
    rows: list[dict] = []
    for rid, title in _ROWS:
        if rid in present:
            status, detail = RowStatus.CHECKING, ""
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


async def _port_hit(token: str, url: str) -> bool:
    """端口候选出网复测

    - 探测结果无 proxy 键错误即该端口可出网
    """
    _, errors = await attempt_channel(token, url)
    return TelegramFieldKey.PROXY not in errors


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


async def _alive_ports(
    cfg: str, reg: dict, stop: Callable[[], bool], frame: Callable[[dict], None]
) -> list[int]:
    """探活本地监听端口并渲染端口行

    - TCP 存活只说明端口有进程监听，能否出网由结论行复测
    - 回环探活并发，总时长约等于单个预算 0.5s
    - stop 为真时返回空列表，调用方据此中止
    """
    sources = dict.fromkeys(
        p for p in (extract_port(cfg), extract_port(str(reg["server"]))) if p
    )
    ports = list(sources) or list(_FALLBACK_PORTS)

    ups = list(await asyncio.gather(*(asyncio.to_thread(port_alive, p) for p in ports)))
    if stop():
        return []
    alive = [p for p, up in zip(ports, ups, strict=True) if up]
    marks = [
        f"{p} {CheckMessage.DIAG_PORT_ALIVE if up else CheckMessage.DIAG_PORT_DEAD}"
        for p, up in zip(ports, ups, strict=True)
    ]
    suffix = f" {CheckMessage.DIAG_PORT_FALLBACK}" if not sources else ""
    frame(
        {
            "id": RowId.PORT,
            "status": RowStatus.OK if alive else RowStatus.FAIL,
            "detail": "  ".join(marks) + suffix,
        }
    )
    return alive


def _advice_frame(channels: Sequence[Channel], alt: str | None) -> dict:
    """组装诊断结论帧

    - 复测命中本次已探测的端点即按抖动通过，不发断链标记
    - 通道红行保持首探结论，转绿的只有结论行
    """
    if alt is not None and is_flap_hit(channels, alt):
        return {
            "id": RowId.ADVICE,
            "status": RowStatus.OK,
            "detail": CheckMessage.DIAG_ADVICE_FLAP,
        }
    return {
        "id": RowId.ADVICE,
        "status": RowStatus.FAIL,
        "detail": CheckMessage.DIAG_ADVICE_ALT.format(url=alt)
        if alt
        else CheckMessage.DIAG_ADVICE_NONE,
        FrameKey.BROKEN: True,
    }


async def _retest_ports(
    alive: list[int], token: str, stop: Callable[[], bool]
) -> str | None:
    """存活端口并发复测

    - 按端口序取首个可出网地址，其余在测任务取消并等结束
    - 返回可出网地址，stop 为真返回 None
    """
    cands = [f"http://127.0.0.1:{p}" for p in alive[:_ALT_RETEST_LIMIT]]
    tasks = [asyncio.ensure_future(_port_hit(token, url)) for url in cands]
    alt: str | None = None
    try:
        for url, task in zip(cands, tasks, strict=True):
            if stop():
                return None
            if await task:
                alt = url
                break
    finally:
        stragglers = [t for t in tasks if not t.done()]
        for t in stragglers:
            t.cancel()
        if stragglers:
            await asyncio.gather(*stragglers, return_exceptions=True)
    return alt


async def diagnose_flow(
    configured_proxy: str = "",
    token: str = "",
    emit: Callable[[dict], None] | None = None,
    stop_check: Callable[[], bool] | None = None,
) -> None:
    """执行一轮网络诊断

    - 通道探测走 run_channels，端口复测与结论行在本模块补齐
    - 任一通道可用即通过，全部失败才扫本机端口复测
    - stop_check 为真时中止并取消在测任务，不输出结论
    """
    frame = emit or _never_emit
    stop = stop_check or _never_stop

    reg = registry_proxy()
    detected = detect_system_proxy()
    cfg = configured_proxy.strip()

    channels = plan_channels(cfg, detected)

    # 首帧把通道行点亮为检测中即启动界面倒计时，引擎导入费须在这之前付完
    preload_engine()
    frame({FrameKey.ROWS: _diagnose_plan(channels, sys_deduped(cfg, detected))})

    outcome = await run_channels(
        channels, _diagnose_probe(token), frame, via_label, stop
    )
    if stop():
        return

    if outcome.passed:
        # 直连救场的"可达"帧已由公共核心发出，这里只补收尾两行
        frame({"id": RowId.PORT, "status": RowStatus.SKIP, "detail": CheckMessage.SKIP})
        frame(
            {
                "id": RowId.ADVICE,
                "status": RowStatus.OK,
                "detail": CheckMessage.ADVICE_OK,
            }
        )
        return

    frame({"id": RowId.PORT, "status": RowStatus.CHECKING, "detail": ""})
    alive = await _alive_ports(cfg, reg, stop, frame)
    if stop():
        return

    # 诊断结论：只对"配置可达"负责，端口行存活不等于通道可用
    frame({"id": RowId.ADVICE, "status": RowStatus.CHECKING, "detail": ""})
    alt = await _retest_ports(alive, token, stop)
    if stop():
        return
    frame(_advice_frame(channels, alt))
