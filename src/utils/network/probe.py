# src/utils/network/probe.py
"""网络探测共享引擎

- 提供候选通道规划、端口探活与进度表行定义
- 连通校验与网络诊断共用
"""

import socket
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from messages import CheckMessage


class RowStatus:
    """表格行五态

    - 诊断窗与校验窗共用的行状态协议
    """

    PENDING = "pending"
    CHECKING = "checking"
    OK = "ok"
    FAIL = "fail"
    SKIP = "skip"


class FieldKey:
    """探测错误字典的键协议

    - 区分 proxy 错与 token 错，禁止跨模块裸写
    - proxy 兼作向导标红字段键，token 不进面板仅作致命判定
    """

    PROXY = "proxy"
    TOKEN = "token"


class RowId:
    """进度表行协议串

    - 行 id 即通道 kind 或收尾行名，禁止跨模块裸写
    """

    CFG = "cfg"
    SYS = "sys"
    DIRECT = "direct"
    LOCAL = "local"
    PORT = "port"
    ADVICE = "advice"


class FrameKey:
    """进度帧的键协议

    - 整表帧判别键与断链标记键
    """

    ROWS = "rows"
    BROKEN = "broken"


_PORT_TIMEOUT = 0.5  # 回环 TCP 探活上限：本机进程秒回，半秒已极宽

# 通道级探测超时预算（秒）
_PROBE_BUDGET = 6.0  # 代理通道全程：SOCKS 握手 + TLS + getMe
_PROBE_BUDGET_DIRECT = 3.0  # 直连被墙时必然等满，预算取短以快速失败

# 常见本地代理软件默认监听端口（Clash/v2rayN/mihomo 等）
_PROXY_PORTS = (7890, 7897, 7898, 7893, 10808, 10809, 8118, 20171, 20172)


@dataclass(frozen=True)
class Channel:
    """通道候选

    - kind 为 cfg/sys/direct
    - url 空串表示直连
    """

    kind: str
    url: str


def plan_channels(configured: str, sys_proxy: str | None) -> list[Channel]:
    """规划候选代理通道

    - 顺序为配置代理、系统代理、直连
    - 配置为空则不生成配置通道
    - 系统代理已开启即入列，与配置同址也各测各的
    - 直连恒为最后一项
    """
    cfg = configured.strip()
    channels = [Channel(RowId.CFG, cfg)] if cfg else []
    if sys_proxy:
        channels.append(Channel(RowId.SYS, sys_proxy))
    channels.append(Channel(RowId.DIRECT, ""))
    return channels


def via_label(ch: Channel) -> str:
    """通道显示名

    - 直连不带地址，代理一律带地址，校验与诊断两轮共用
    """
    if not ch.url:
        return CheckMessage.VIA_DIRECT
    if ch.kind == RowId.CFG:
        return CheckMessage.VIA_CFG.format(proxy=ch.url)
    return CheckMessage.VIA_SYSTEM.format(proxy=ch.url)


def probe_budget(url: str) -> float:
    """通道探测预算

    - 直连失败响应快，取较短预算
    - 代理首次握手慢，取较长预算
    """
    return _PROBE_BUDGET_DIRECT if not url else _PROBE_BUDGET


# 校验表行序：行 id 即 Channel.kind，port/local/advice 为收尾行，与发帧顺序一致
_VERIFY_ROWS = (
    (RowId.CFG, CheckMessage.ROW_CFG, RowStatus.FAIL, CheckMessage.CFG_EMPTY),
    (RowId.SYS, CheckMessage.ROW_SYS, RowStatus.FAIL, CheckMessage.SYS_UNAVAILABLE),
    (RowId.DIRECT, CheckMessage.ROW_DIRECT, RowStatus.PENDING, ""),
    (RowId.PORT, CheckMessage.ROW_PORT, RowStatus.PENDING, ""),
    (RowId.LOCAL, CheckMessage.ROW_LOCAL, RowStatus.PENDING, ""),
    (RowId.ADVICE, CheckMessage.ROW_ADVICE, RowStatus.PENDING, ""),
)


def verify_skeleton() -> list[dict]:
    """六行等待态占位表

    - 校验计划生成前的初始显示
    """
    return [
        {"id": rid, "title": title, "status": RowStatus.PENDING, "detail": ""}
        for rid, title, _, _ in _VERIFY_ROWS
    ]


_TAIL_ROWS = (RowId.LOCAL, RowId.PORT, RowId.ADVICE)


def verify_plan(
    channels: Sequence[Channel],
    reuse: bool = False,
    local_frame: dict | None = None,
) -> list[dict]:
    """生成校验首帧整表

    - 待探测通道标进行中，缺席与复用行直接给出状态
    - 不探测的通道按原因直接给结论
    - reuse 为真表示仅复查 token，未涉及的通道行标复用已验证通道
    - local_frame 传入则本地行随首帧先行显示
    """
    kinds = {ch.kind for ch in channels}
    budgets = {ch.kind: probe_budget(ch.url) for ch in channels}
    rows: list[dict] = []
    for rid, title, absent_status, absent_detail in _VERIFY_ROWS:
        if rid in kinds:
            status, detail = RowStatus.CHECKING, ""
        elif rid == RowId.LOCAL and local_frame is not None:
            status, detail = local_frame["status"], local_frame["detail"]
        elif rid in _TAIL_ROWS:
            status, detail = RowStatus.PENDING, ""
        elif reuse:
            status, detail = RowStatus.SKIP, CheckMessage.VERIFY_REUSE
        else:
            status, detail = absent_status, absent_detail
        row = {"id": rid, "title": title, "status": status, "detail": detail}
        if rid in budgets:
            row["budget"] = int(budgets[rid])
        rows.append(row)
    return rows


def extract_port(address: str) -> int | None:
    """从裸地址或分号串里提取端口"""
    for token in str(address).replace("=", ";").split(";"):
        # 取第一个合法值
        item = token.strip().rsplit(":", 1)[-1].split("/")[0]
        if item.isdigit():
            return int(item)
    return None


def port_alive(port: int) -> bool:
    """TCP 能否连上本机端口"""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=_PORT_TIMEOUT):
            return True
    except OSError:
        return False


def _probe_ports(ports: Sequence[int]) -> list[bool]:
    """并发探活一组端口"""
    if not ports:
        return []
    with ThreadPoolExecutor(max_workers=len(ports)) as pool:
        return list(pool.map(port_alive, ports))


def scan_proxy_ports() -> list[str]:
    """扫描本机常见代理端口

    - 返回存活端口对应的 http URL 列表
    - TCP 存活只说明端口有进程监听，能否出网须由调用方以真实请求复测
    """
    alive = _probe_ports(_PROXY_PORTS)
    return [
        f"http://127.0.0.1:{port}"
        for port, up in zip(_PROXY_PORTS, alive, strict=True)
        if up
    ]
