# src/utils/network/probe.py
"""网络探测共享引擎

- 候选通道规划与进度表行
- 连通校验与网络诊断共用
"""

from collections.abc import Sequence
from dataclasses import dataclass

from finshin_sdk.domain import ConfigKey, FieldKey, ProxyMode
from skin.messages import CheckMessage


class RowStatus:
    """表格行五态"""

    PENDING = "pending"
    CHECKING = "checking"
    OK = "ok"
    FAIL = "fail"
    SKIP = "skip"


class RowId:
    """进度表行协议串"""

    CFG = "cfg"
    SYS = "sys"
    DIRECT = "direct"
    LOCAL = "local"
    ADVICE = "advice"


class FrameKey:
    """进度帧的键协议"""

    ROWS = "rows"
    HEAD = "head"
    BROKEN = "broken"


# 通道级探测超时预算（秒）
_PROBE_BUDGET = 9.0  # 代理通道全程：引擎导入已在起表前预触，窗口内只剩网络时间，TUN 冷启动首连慢取宽避免误判
_PROBE_BUDGET_DIRECT = 3.0  # 直连被墙时必然等满，预算取短以快速失败

# 单路模式的配置值 → 通道行 id，缺项值按自动全探处理
_SINGLE_KINDS: dict[str, str] = {
    ProxyMode.CFG: RowId.CFG,
    ProxyMode.SYS: RowId.SYS,
    ProxyMode.DIRECT: RowId.DIRECT,
}


@dataclass(frozen=True)
class Channel:
    """通道候选

    - 地址为空串表示直连
    """

    kind: str
    url: str


def _endpoint_key(url: str) -> tuple[str, str]:
    """提取代理地址的主机与端口"""
    body = url.strip().lower().split("://", 1)[-1].rstrip("/")
    host, _, port = body.rpartition(":")
    return host, port


def _same_endpoint(left: str, right: str) -> bool:
    """两个代理地址是否同一主机与端口"""
    return _endpoint_key(left) == _endpoint_key(right)


def sys_deduped(configured: str, sys_proxy: str | None) -> bool:
    """配置与系统代理是否同端点"""
    cfg = configured.strip()
    if not cfg or not sys_proxy:
        return False
    return _same_endpoint(cfg, sys_proxy)


# 会探到配置通道的模式，即用户填的代理地址派得上用场的两档
_CFG_TESTED_MODES = (ProxyMode.AUTO, ProxyMode.CFG)

# 会探到系统代理通道的模式，即注册表那一项有关的档位
_SYS_TESTED_MODES = (ProxyMode.AUTO, ProxyMode.SYS)


def uses_system_proxy(mode: str) -> bool:
    """本模式是否会探测系统代理通道"""
    return mode in _SYS_TESTED_MODES


def uses_configured_proxy(mode: str) -> bool:
    """本模式是否会探测配置代理通道"""
    return mode in _CFG_TESTED_MODES


def fault_row_of(mode: str) -> str:
    """代理不通时标红哪一行"""
    # 代理项藏掉的档位，报错不能落在看不见的那行上
    return FieldKey.PROXY if uses_configured_proxy(mode) else ConfigKey.PROXY_MODE


def plan_channels(
    configured: str, sys_proxy: str | None, *, mode: str = ProxyMode.AUTO
) -> list[Channel]:
    """规划候选代理通道

    - 单路模式只生成选定通道
    - 自动模式按配置代理、系统代理、直连排序
    - 配置为空则不生成配置通道
    - 系统代理与配置同端点时去重
    """
    cfg = configured.strip()

    # 坏值按自动全探处理，标红交给本地类型校验
    single = _SINGLE_KINDS.get(mode)
    if single is not None:
        return _single_channels(single, cfg, sys_proxy)
    channels = [Channel(RowId.CFG, cfg)] if cfg else []

    # 同端点并发双探会在同一个代理进程与出口互抢
    if sys_proxy and not sys_deduped(cfg, sys_proxy):
        channels.append(Channel(RowId.SYS, sys_proxy))
    channels.append(Channel(RowId.DIRECT, ""))
    return channels


def _single_channels(kind: str, cfg: str, sys_proxy: str | None) -> list[Channel]:
    """单路模式的候选表

    - 选路缺地址即空表
    """
    if kind == RowId.CFG:
        return [Channel(RowId.CFG, cfg)] if cfg else []
    if kind == RowId.SYS:
        return [Channel(RowId.SYS, sys_proxy)] if sys_proxy else []
    return [Channel(RowId.DIRECT, "")]


def via_label(ch: Channel) -> str:
    """通道显示名"""
    if not ch.url:
        return CheckMessage.VIA_DIRECT
    if ch.kind == RowId.CFG:
        return CheckMessage.VIA_CFG.format(proxy=ch.url)
    return CheckMessage.VIA_SYSTEM.format(proxy=ch.url)


def probe_budget(url: str) -> float:
    """通道探测预算"""
    return _PROBE_BUDGET_DIRECT if not url else _PROBE_BUDGET


# 校验表行序：行 id 即 Channel.kind，local/advice 为收尾行，与发帧顺序一致
_VERIFY_ROWS = (
    (RowId.CFG, CheckMessage.ROW_CFG, RowStatus.FAIL, CheckMessage.CFG_EMPTY),
    (RowId.SYS, CheckMessage.ROW_SYS, RowStatus.FAIL, CheckMessage.SYS_UNAVAILABLE),
    (RowId.DIRECT, CheckMessage.ROW_DIRECT, RowStatus.PENDING, ""),
    (RowId.LOCAL, CheckMessage.ROW_LOCAL, RowStatus.PENDING, ""),
    (RowId.ADVICE, CheckMessage.ROW_ADVICE, RowStatus.PENDING, ""),
)


def verify_skeleton() -> list[dict]:
    """等待态占位表

    - 校验计划生成前的初始显示
    """
    return [
        {"id": rid, "title": title, "status": RowStatus.PENDING, "detail": ""}
        for rid, title, _, _ in _VERIFY_ROWS
    ]


_TAIL_ROWS = (RowId.LOCAL, RowId.ADVICE)

# 三路网络通道的行 id，未起表的档位按它点名
NETWORK_ROWS = tuple(rid for rid, *_ in _VERIFY_ROWS if rid not in _TAIL_ROWS)


def single_row_of(mode: str) -> tuple[str, str, str] | None:
    """单路模式的通道行

    - 返回行 id、标题与缺席结论句
    - 自动模式返回 None，表保持三路全行
    """
    kind = _SINGLE_KINDS.get(mode)
    if kind is None:
        return None
    return {
        RowId.CFG: (RowId.CFG, CheckMessage.ROW_CFG, CheckMessage.MODE_CFG_ABSENT),
        RowId.SYS: (RowId.SYS, CheckMessage.ROW_SYS, CheckMessage.MODE_SYS_ABSENT),
        RowId.DIRECT: (RowId.DIRECT, CheckMessage.ROW_DIRECT, ""),
    }[kind]


def verify_plan(
    channels: Sequence[Channel],
    local_frame: dict | None = None,
    sys_dedup: bool = False,
    single: tuple[str, str, str] | None = None,
) -> list[dict]:
    """生成连通整表首帧

    - 待探测通道标进行中，缺席与免测的行按原因直接给出终态
    - 同端点去重时系统代理行标去重而非缺席
    - 单路模式只留选定通道行，尾行按 local_frame 与结论行决定
    - 没给本地校验结果就不出本地行，诊断那一轮走的就是这一档
    """
    kinds = {ch.kind for ch in channels}
    budgets = {ch.kind: probe_budget(ch.url) for ch in channels}
    rows: list[dict] = []
    for rid, title, absent_status, absent_detail in _VERIFY_ROWS:
        if rid == RowId.LOCAL and local_frame is None:
            continue
        if single is not None and rid not in (single[0], RowId.LOCAL, RowId.ADVICE):
            continue
        if rid in kinds:
            status, detail = RowStatus.CHECKING, ""
        elif single is not None and rid == single[0]:
            status, detail, title = RowStatus.FAIL, single[2], single[1]
        elif rid == RowId.SYS and sys_dedup:
            status, detail = RowStatus.SKIP, CheckMessage.SYS_DEDUP
        elif rid == RowId.LOCAL and local_frame is not None:
            status, detail = local_frame["status"], local_frame["detail"]
        elif rid in _TAIL_ROWS:
            status, detail = RowStatus.PENDING, ""
        else:
            status, detail = absent_status, absent_detail
        row = {"id": rid, "title": title, "status": status, "detail": detail}
        if rid in budgets:
            row["budget"] = int(budgets[rid])
        rows.append(row)
    return rows
