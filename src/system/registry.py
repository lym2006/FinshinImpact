# src/system/registry.py
"""注册表系统代理读取

- 读 ProxyEnable 与 ProxyServer/PriProxy 原始值成对回传
"""

import sys
from typing import NamedTuple

_PROXY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"

# 注册表代理值名，与 packaging/launcher.py 独立副本同值（exe 不导入 src）
_PROXY_ENABLE_VALUE = "ProxyEnable"
_PROXY_SERVER_VALUE = "ProxyServer"
_PROXY_PRI_VALUE = "PriProxy"


class _ProxyRegistry(NamedTuple):
    """系统代理注册表原始值对"""

    enable: int | None  # None 代表读取失败或非 Windows，按未开启处理
    server: str


def read_proxy_registry() -> _ProxyRegistry:
    """读注册表系统代理开关与地址

    - 任一环节失败按 (None, "") 回退
    - ProxyServer 与 PriProxy 皆有值时取先命中的 ProxyServer
    """
    if sys.platform != "win32":
        return _ProxyRegistry(None, "")

    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _PROXY_KEY) as key:
            enable = winreg.QueryValueEx(key, _PROXY_ENABLE_VALUE)[0]
            for value_name in (_PROXY_SERVER_VALUE, _PROXY_PRI_VALUE):
                try:
                    raw = str(winreg.QueryValueEx(key, value_name)[0]).strip()
                except OSError:
                    continue
                if raw:
                    return _ProxyRegistry(enable, raw)
            return _ProxyRegistry(enable, "")
    except OSError:
        return _ProxyRegistry(None, "")
