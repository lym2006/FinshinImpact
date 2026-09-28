# src/utils/system_proxy.py
"""系统代理探测

- 读取注册表系统代理并格式化为会话可用 URL
- 提供配置留空时的自动兜底入口
"""

import sys

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


def registry_proxy() -> dict:
    """读注册表系统代理开关与地址，失败按未开启处理"""
    info = {"enable": None, "server": ""}
    if sys.platform != "win32":
        return info
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _PROXY_KEY) as key:
            info["enable"] = winreg.QueryValueEx(key, "ProxyEnable")[0]
            for value_name in ("ProxyServer", "PriProxy"):
                try:
                    raw = str(winreg.QueryValueEx(key, value_name)[0]).strip()
                except OSError:
                    continue
                if raw:
                    info["server"] = raw
                    break
    except OSError:
        pass
    return info


def detect_system_proxy() -> str | None:
    """探测系统代理

    ProxyEnable=1 且地址可解析才返回 URL。
    """
    reg = registry_proxy()
    if not reg["enable"]:
        return None
    address = _pick_from_entries(str(reg["server"]))
    return _to_url(address) if address else None
