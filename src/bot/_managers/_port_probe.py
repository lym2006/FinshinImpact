# src/bot/_managers/_port_probe.py
"""本机端口复测

- 校验全挂时扫本机代理端口并复测出网
- 渲染端口行进度帧，仅探测提示不自动采用
"""

import asyncio

from gui.mediator import gui_bridge
from messages import CheckMessage
from utils.connectivity import attempt_channel
from utils.net_probe import FieldKey, RowId, RowStatus, scan_proxy_ports
from utils.verify_flow import ChannelOutcome


async def verify_port_row(outcome: ChannelOutcome, token: str, token_only: bool) -> str:
    """渲染本机端口复测行

    - 通道判通则标跳过
    - 全挂才扫本机端口：仅探测复测，不自动采用、不写配置
    - 返回命中的代理 URL，无则空串
    """
    if outcome.passed:
        gui_bridge.verify_progress.emit(
            {
                "id": RowId.PORT,
                "status": RowStatus.SKIP,
                "detail": CheckMessage.SKIP,
            }
        )
        return ""

    if FieldKey.PROXY not in outcome.errors or token_only:
        return ""

    gui_bridge.verify_progress.emit(
        {"id": RowId.PORT, "status": RowStatus.CHECKING, "detail": ""}
    )
    port_hint, alive = await _probe_ports(token)
    if port_hint:
        status, detail = (
            RowStatus.OK,
            CheckMessage.VERIFY_PORT_HIT.format(url=port_hint),
        )
    elif not alive:
        status, detail = RowStatus.FAIL, CheckMessage.VERIFY_PORT_EMPTY
    else:
        status, detail = RowStatus.FAIL, CheckMessage.VERIFY_PORT_NONE
    gui_bridge.verify_progress.emit(
        {"id": RowId.PORT, "status": status, "detail": detail}
    )
    return port_hint


async def _probe_ports(token: str) -> tuple[str, int]:
    """本机端口扫描复测

    - 返回 (首个 getMe 实测可通的 URL 或空串, 存活端口数)
    - TCP 存活不等于可出网，复测不过不提示
    - 全端口并发发射、按列表序收口：端口序即优先级，定案后剩余取消等落地
    """
    urls = await asyncio.to_thread(scan_proxy_ports)
    if not urls:
        return "", 0
    tasks = [asyncio.ensure_future(attempt_channel(token, url)) for url in urls]
    hit = ""
    try:
        # 按列表序逐个取结局：首个可通即定案，前面的已败不必再看
        for task in tasks:
            resolved, _ = await task
            if resolved is not None:
                hit = resolved
                break
    finally:
        # 定案/异常都清场：在途的掐掉并等落地，防 destroyed 噪声
        stragglers = [t for t in tasks if not t.done()]
        for task in stragglers:
            task.cancel()
        if stragglers:
            await asyncio.gather(*stragglers, return_exceptions=True)
    return hit, len(urls)
