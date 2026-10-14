# packaging/launch/proxy.py
"""安装期系统代理注入

- 注册表代理临时写入环境变量，仅供安装期子进程使用
"""

import os

# 注册表代理值名，与 src/utils/system_proxy.py 同值
_PROXY_ENABLE_VALUE = "ProxyEnable"
_PROXY_SERVER_VALUE = "ProxyServer"


def apply_system_proxy() -> None:
    """注册表系统代理临时注入环境变量

    - 安装下载随其走代理
    - 仅供安装期子进程使用，_launch 会剔除
    """
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as key:
            if not winreg.QueryValueEx(key, _PROXY_ENABLE_VALUE)[0]:
                return
            raw = str(winreg.QueryValueEx(key, _PROXY_SERVER_VALUE)[0]).strip()
    except OSError:
        return

    # 兼容 "127.0.0.1:7890" 与 "http=…;https=…" 两种写法
    proxy = raw
    for part in raw.split(";"):
        name, _, value = part.partition("=")
        if name.strip().lower() in ("https", "http", "all") and value.strip():
            proxy = value.strip()
            break
    if not proxy:
        return
    if "://" not in proxy:
        proxy = f"http://{proxy}"
    os.environ["HTTP_PROXY"] = os.environ["HTTPS_PROXY"] = proxy
