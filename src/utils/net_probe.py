# src/utils/net_probe.py
"""网络探测共享引擎

- 通道阶梯规划与本地端口探活单源，连通校验与网络诊断共用
- 定义行状态集与校验窗行骨架
"""

import socket
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from messages import CheckMessage


class RowStatus:
    """表格行五态：诊断窗与校验窗共用的行状态协议"""

    PENDING = "pending"
    CHECKING = "checking"
    OK = "ok"
    FAIL = "fail"
    SKIP = "skip"


class FieldKey:
    """探测错误字典的键协议：兼作向导标红的字段键，禁止跨模块裸写"""

    PROXY = "proxy"
    TOKEN = "telegram_token"


class RowId:
    """进度表行协议串：行 id 即通道 kind 或收尾行名，禁止跨模块裸写"""

    CFG = "cfg"
    SYS = "sys"
    DIRECT = "direct"
    LOCAL = "local"
    PORT = "port"
    ADVICE = "advice"


class FrameKey:
    """进度帧的键协议：整表帧判别键与断链标记键"""

    ROWS = "rows"
    BROKEN = "broken"


_PORT_TIMEOUT = 0.5  # 回环 TCP 探活上限：本机进程秒回，半秒已极宽

# 常见本地代理软件默认监听端口（Clash/v2rayN/mihomo 等）
_PROXY_PORTS = (7890, 7897, 7898, 7893, 10808, 10809, 8118, 20171, 20172)


@dataclass(frozen=True)
class Channel:
    """通道候选：kind 为 cfg/sys/direct，url 空串表示直连"""

    kind: str
    url: str


def plan_channels(configured: str, sys_proxy: str | None) -> list[Channel]:
    """规划通道阶梯：配置代理 → 系统代理 → 直连

    配置为空不出 cfg 项，系统代理与配置同址去重，直连恒为末位兜底。
    """
    cfg = configured.strip()
    channels = [Channel(RowId.CFG, cfg)] if cfg else []
    if sys_proxy and sys_proxy != cfg:
        channels.append(Channel(RowId.SYS, sys_proxy))
    channels.append(Channel(RowId.DIRECT, ""))
    return channels


def via_label(ch: Channel) -> str:
    """通道称谓：直连裸称，代理类一律带地址，两轮表格与日志共用"""
    if not ch.url:
        return CheckMessage.VIA_DIRECT
    if ch.kind == RowId.CFG:
        return CheckMessage.VIA_CFG.format(proxy=ch.url)
    return CheckMessage.VIA_SYSTEM.format(proxy=ch.url)


# 校验表行序：行 id 即 Channel.kind，port/local/advice 为收尾行，与发帧顺序一致
_VERIFY_ROWS = (
    (RowId.CFG, CheckMessage.ROW_CFG, CheckMessage.CFG_EMPTY),
    (RowId.SYS, CheckMessage.ROW_SYS, CheckMessage.SYS_UNAVAILABLE),
    (RowId.DIRECT, CheckMessage.ROW_DIRECT, ""),
    (RowId.PORT, CheckMessage.ROW_PORT, ""),
    (RowId.LOCAL, CheckMessage.ROW_LOCAL, ""),
    (RowId.ADVICE, CheckMessage.ROW_ADVICE, ""),
)


def verify_skeleton() -> list[dict]:
    """全等待态六行骨架：校验计划到达前的占位"""
    return [
        {"id": rid, "title": title, "status": RowStatus.PENDING, "detail": ""}
        for rid, title, _ in _VERIFY_ROWS
    ]


_TAIL_ROWS = (RowId.LOCAL, RowId.PORT, RowId.ADVICE)


def verify_plan(channels: Sequence[Channel], reuse: bool = False) -> list[dict]:
    """生成校验进度表骨架

    与诊断窗同款五态；阶梯里没有的通道行直接给定态，不再发探测帧。
    reuse=True 表示仅复查 token：未涉及的通道行标"复用已验证通道"。
    收尾行不参与通道阶梯，恒为等待态由调用方逐帧点亮。
    """
    kinds = {ch.kind for ch in channels}
    rows: list[dict] = []
    for rid, title, missing in _VERIFY_ROWS:
        # 收尾行恒为等待态；未出现的通道行按复查/缺席给定态
        if rid in kinds or rid in _TAIL_ROWS:
            status, detail = RowStatus.PENDING, ""
        elif reuse:
            status, detail = RowStatus.SKIP, CheckMessage.VERIFY_REUSE
        else:
            status, detail = RowStatus.FAIL, missing
        rows.append({"id": rid, "title": title, "status": status, "detail": detail})
    return rows


def extract_port(address: str) -> int | None:
    """从裸地址或分号串里提取端口，取第一个合法值"""
    for token in str(address).replace("=", ";").split(";"):
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
    """并发探活一组端口，结果与输入顺序一一对应"""
    if not ports:
        return []
    with ThreadPoolExecutor(max_workers=len(ports)) as pool:
        return list(pool.map(port_alive, ports))


def scan_proxy_ports() -> list[str]:
    """扫描本机常见代理端口

    返回存活端口对应的 http URL 列表。
    TCP 存活只证明进程在听，能否出网须由调用方以真实请求复测。
    """
    alive = _probe_ports(_PROXY_PORTS)
    return [
        f"http://127.0.0.1:{port}"
        for port, up in zip(_PROXY_PORTS, alive, strict=True)
        if up
    ]
