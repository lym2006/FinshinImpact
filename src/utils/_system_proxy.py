# src/utils/_system_proxy.py
"""系统代理探测（内部实现）

- 读取注册表系统代理并格式化为会话可用 URL
- 提供配置留空时的自动兜底入口
"""

import socket
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any

_PROXY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"


def _pick_from_entries(raw: str) -> str | None:
    """提取代理地址

    兼容分协议格式，优先 https 条目。
    """
    entries: dict[str, str] = {}
    singles: list[str] = []
    for part in raw.split(";"):
        item = part.strip()
        if not item or item.startswith("<"):
            continue  # <-loopback> 之类的控制标记
        if "=" in item:
            name, _, value = item.partition("=")
            if value.strip():
                entries[name.strip().lower()] = value.strip()
        else:
            singles.append(item)
    for name in ("https", "http", "all"):
        if name in entries:
            return entries[name]
    return singles[0] if singles else None


def _to_url(address: str) -> str | None:
    """裸地址补 http scheme

    mixed 端口 HTTP/SOCKS 双协议，统一按 http。
    """
    address = address.strip()
    if not address:
        return None
    if "://" in address:
        return address
    return f"http://{address}"


def detect_system_proxy() -> str | None:
    """探测系统代理

    ProxyEnable=1 且地址可解析才返回 URL。
    """
    if sys.platform != "win32":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _PROXY_KEY) as key:
            enabled: Any = winreg.QueryValueEx(key, "ProxyEnable")[0]
            if not enabled:
                return None
            raw = ""
            for value_name in ("ProxyServer", "PriProxy"):
                try:
                    raw = str(winreg.QueryValueEx(key, value_name)[0]).strip()
                except OSError:
                    continue
                if raw:
                    break
    except OSError:
        return None
    address = _pick_from_entries(raw)
    return _to_url(address) if address else None
# ==================== 端口扫描 ====================

# 常见本地代理软件默认监听端口（Clash/v2rayN/mihomo 等）
_PROXY_PORTS = (7890, 7897, 7898, 7893, 10808, 10809, 8118, 20171, 20172)


def _port_alive(port: int) -> bool:
    """TCP 能否连上本机端口"""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.8):
            return True
    except OSError:
        return False


def scan_proxy_ports() -> list[str]:
    """扫描本机常见代理端口

    线程池并发探活，返回存活端口对应的 http URL 列表；TCP 存活
    只证明进程在听，能否出网须由调用方以真实请求复测。
    """
    with ThreadPoolExecutor(max_workers=len(_PROXY_PORTS)) as pool:
        alive = list(pool.map(_port_alive, _PROXY_PORTS))
    return [f"http://127.0.0.1:{p}" for p, ok in zip(_PROXY_PORTS, alive, strict=True) if ok]
