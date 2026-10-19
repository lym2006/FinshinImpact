# packaging/launch/proxy.py
"""安装期系统代理

- 读注册表代理值成 URL
- 把注册表代理注入环境变量，仅供安装期子进程使用
"""

import os

# 注册表代理值名，与 src/system/registry.py 同值（exe 不导入 src）
_PROXY_ENABLE_VALUE = "ProxyEnable"
_PROXY_SERVER_VALUE = "ProxyServer"

_PROXY_SCHEME = "http://"  # 注册表只记地址与端口时按 HTTP 代理补齐协议头


def system_proxy_url() -> str | None:
    """注册表系统代理 URL

    - ProxyEnable 为 0 或读不到值时返回 None
    - 兼容 "127.0.0.1:7890" 与 "http=…;https=…" 两种写法
    """
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as key:
            if not winreg.QueryValueEx(key, _PROXY_ENABLE_VALUE)[0]:
                return None
            raw = str(winreg.QueryValueEx(key, _PROXY_SERVER_VALUE)[0]).strip()
    except OSError:
        return None

    proxy = raw
    for part in raw.split(";"):
        name, _, value = part.partition("=")
        if name.strip().lower() in ("https", "http", "all") and value.strip():
            proxy = value.strip()
            break
    if not proxy:
        return None
    if "://" not in proxy:
        proxy = f"{_PROXY_SCHEME}{proxy}"
    return proxy


def apply_system_proxy() -> None:
    """注册表系统代理临时注入环境变量

    - 仅供安装期子进程使用，_launch 会剔除
    - 启动器自身取数走 netio 的 opener，不读这份环境变量
    """
    proxy = system_proxy_url()
    if not proxy:
        return
    os.environ["HTTP_PROXY"] = os.environ["HTTPS_PROXY"] = proxy
