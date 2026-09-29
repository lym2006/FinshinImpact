# src/utils/diagnose.py
"""网络连通诊断

- 通道阶梯调度复用 verify_flow 公共核心，探测用假 token 只判网络层
- 缺席通道以占位入梯：前级已通时照常亮"跳过"，未被短路才给缺席结论
- 端口复测与直连专属措辞是诊断独有语义，收口逻辑留在本模块
"""

import asyncio
import urllib.error
import urllib.request
from collections.abc import Callable

from messages import CheckMessage

from .net_probe import (
    Channel,
    FieldKey,
    FrameKey,
    RowId,
    RowStatus,
    extract_port,
    port_alive,
    via_label,
)
from .system_proxy import detect_system_proxy, registry_proxy
from .verify_flow import run_channels

_PROBE_URL = "https://api.telegram.org/bot0:probe/getMe"
_PROBE_TIMEOUT = 2.0  # 单通道出网探测上限：通亚秒级返回，不通快速放弃

# 仅当配置项与系统注册表都拿不到端口时，才回退扫描这组常见默认值
_FALLBACK_PORTS = (7890, 7897, 7898)
# 结论行最多复测几个存活端口，防全挂场景串行等待过长
_ALT_RETEST_LIMIT = 3

# 固定骨架：id 与标题（界面与生成器共用，顺序即展示与探测的短路顺序）
# 本地配置行只属校验轮：诊断职责是网络排查，渲染本地结果会误导语义
_ROWS = (
    (RowId.CFG, CheckMessage.ROW_CFG),
    (RowId.SYS, CheckMessage.ROW_SYS),
    (RowId.DIRECT, CheckMessage.ROW_DIRECT),
    (RowId.PORT, CheckMessage.ROW_PORT),
    (RowId.ADVICE, CheckMessage.ROW_ADVICE),
)


def _never_stop() -> bool:
    """默认停止回调：永不中断"""
    return False


def _never_emit(_frame: dict) -> None:
    """无回调占位：独立调用时静默消费帧"""
    return None


def diagnose_plan() -> list[dict]:
    """生成全等待态骨架，界面打开即可渲染"""
    return [
        {"id": rid, "title": title, "status": RowStatus.PENDING, "detail": ""}
        for rid, title in _ROWS
    ]


def _reach(proxy: str | None) -> bool:
    """实测 Telegram 可达

    收到任意 HTTP 状态码即证明网络层已打通
    """
    handlers = []
    if proxy:
        handlers = [urllib.request.ProxyHandler({"http": proxy, "https": proxy})]
    opener = urllib.request.build_opener(*handlers)
    try:
        opener.open(_PROBE_URL, timeout=_PROBE_TIMEOUT)
        return True
    except urllib.error.HTTPError:
        return True
    except Exception:
        return False


# ==================== 核心诊断逻辑 ====================


async def diagnose_flow(
    configured_proxy: str = "",
    emit: Callable[[dict], None] | None = None,
    stop_check: Callable[[], bool] | None = None,
) -> None:
    """跑一轮诊断：阶梯调度进公共核心，诊断独有收口在本地补齐

    缺席通道带预置结论入梯，被前级短路时亮跳过、短路不到才给缺席句。
    全挂才扫端口并复测可用地址。stop_check 在两处网络间隙检查，置真即静默收尾。
    """
    frame = emit or _never_emit
    stop = stop_check or _never_stop
    frame({FrameKey.ROWS: diagnose_plan()})

    reg = registry_proxy()
    detected = detect_system_proxy()
    cfg = configured_proxy.strip()

    # 缺席通道的预置失败句：探针命中即直接返回，不发网络请求
    preset: dict[str, str] = {}
    channels: list[Channel] = []
    channels.append(Channel(RowId.CFG, cfg))
    if not cfg:
        preset[RowId.CFG] = CheckMessage.CFG_EMPTY
    channels.append(Channel(RowId.SYS, detected or ""))
    if not detected:
        preset[RowId.SYS] = CheckMessage.SYS_UNAVAILABLE
    channels.append(Channel(RowId.DIRECT, ""))

    async def probe(ch: Channel) -> tuple[str | None, dict[str, str], str]:
        """探针分派：缺席给预置句，在场走 urllib 假 token 实测"""
        if ch.kind in preset:
            # 缺席通道：预置句作表格显式覆盖，同时进字段错误
            return None, {FieldKey.PROXY: preset[ch.kind]}, preset[ch.kind]
        ok = await asyncio.to_thread(_reach, ch.url or None)
        if ok:
            return ch.url, {}, ""
        # 在场失败：表格句留空，由核心统一拼"称谓：不可达"
        return None, {FieldKey.PROXY: CheckMessage.REACH_FAIL}, ""

    outcome = await run_channels(channels, probe, frame, via_label, stop)
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

    # 本地监听端口：TCP 存活只证明进程在听，能否出网由结论行复测
    frame({"id": RowId.PORT, "status": RowStatus.CHECKING, "detail": ""})
    sources = dict.fromkeys(
        p for p in (extract_port(cfg), extract_port(str(reg["server"]))) if p
    )
    ports = list(sources) or list(_FALLBACK_PORTS)
    alive: list[int] = []
    marks: list[str] = []
    for port in ports:
        if stop():
            return
        up = await asyncio.to_thread(port_alive, port)
        if up:
            alive.append(port)
        marks.append(
            f"{port} {CheckMessage.DIAG_PORT_ALIVE if up else CheckMessage.DIAG_PORT_DEAD}"
        )
    suffix = f" {CheckMessage.DIAG_PORT_FALLBACK}" if not sources else ""
    frame(
        {
            "id": RowId.PORT,
            "status": RowStatus.OK if alive else RowStatus.FAIL,
            "detail": "  ".join(marks) + suffix,
        }
    )

    # 诊断结论：只对"配置可达"负责，端口行存活不等于通道可用
    frame({"id": RowId.ADVICE, "status": RowStatus.CHECKING, "detail": ""})
    alt = ""
    for port in alive[:_ALT_RETEST_LIMIT]:
        if stop():
            return
        url = f"http://127.0.0.1:{port}"
        if await asyncio.to_thread(_reach, url):
            alt = url
            break
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
