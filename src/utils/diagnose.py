# src/utils/diagnose.py
"""网络连通诊断

- 通道并行调度复用 verify_flow 公共核心，探针与校验轮同源同参（真 token 全复用）
- 缺席通道开局静态给定态：配置留空与系统代理未开启当场落定
- 端口复测与收口话术是诊断独有语义，逻辑留在本模块
"""

import asyncio
import time
from collections.abc import Awaitable, Callable, Sequence

from messages import CheckMessage

from .connectivity import attempt_channel
from .logger import get_logger
from .net_probe import (
    Channel,
    FieldKey,
    FrameKey,
    RowId,
    RowStatus,
    extract_port,
    port_alive,
    probe_budget,
    via_label,
)
from .system_proxy import detect_system_proxy, registry_proxy
from .verify_flow import run_channels

# 诊断跑在后台线程的私有 loop，耗时句走此器落 debug
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


def _diagnose_plan(channels: Sequence[Channel]) -> list[dict]:
    """开局整表

    - 在场通道标进行中，缺席行直接给定态
    - 在场判据以实际入梯为准，缺席成因静态可知（配置留空/系统代理未开启）
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

    - 探针同源，无 proxy 键错误即该端口可出网
    """
    _, errors = await attempt_channel(token, url)
    return FieldKey.PROXY not in errors


def _diagnose_probe(
    token: str,
) -> Callable[[Channel], Awaitable[tuple[str | None, dict[str, str], str]]]:
    """造诊断探针

    - 与校验轮共用 attempt_channel，同网络栈、同预算、真 token 实测
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


def _diagnose_channels(cfg: str, detected: str | None) -> list[Channel]:
    """规划在场通道

    - 缺席行由开局帧直接给定态，不入梯
    """
    channels = [Channel(RowId.CFG, cfg)] if cfg else []
    if detected:
        channels.append(Channel(RowId.SYS, detected))
    channels.append(Channel(RowId.DIRECT, ""))
    return channels


async def _alive_ports(
    cfg: str, reg: dict, stop: Callable[[], bool], frame: Callable[[dict], None]
) -> list[int]:
    """探活本地监听端口并渲染端口行

    - TCP 存活只证明进程在听，能否出网由结论行复测
    - 回环探活并发全等：单个预算 0.5s，串行只会把秒数累加成人质
    - stop 置真返回空表，调用方据此静默收尾
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


async def _retest_ports(
    alive: list[int], token: str, stop: Callable[[], bool]
) -> str | None:
    """存活端口并发复测

    - 按端口序取首个可通定案，陪跑取消等落地
    - 返回可出网地址，stop 置真返回 None
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
    """跑一轮诊断

    - 并行调度进公共核心，诊断独有收口在本地补齐
    - 缺席通道静态给定态不入梯
    - 全挂才扫端口并复测可用地址
    - stop_check 置真即静默收尾，公共核心掐掉全部在途探测
    """
    frame = emit or _never_emit
    stop = stop_check or _never_stop

    reg = registry_proxy()
    detected = detect_system_proxy()
    cfg = configured_proxy.strip()

    channels = _diagnose_channels(cfg, detected)
    frame({FrameKey.ROWS: _diagnose_plan(channels)})

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
    frame(
        {
            "id": RowId.ADVICE,
            "status": RowStatus.FAIL,
            "detail": CheckMessage.DIAG_ADVICE_ALT.format(url=alt)
            if alt
            else CheckMessage.DIAG_ADVICE_NONE,
            FrameKey.BROKEN: True,
        }
    )
