# packaging/netio.py
"""启动器侧取数通道

- 给出忽略环境代理的 opener
- 给出显式走指定代理的 opener
"""

import urllib.request

Opener = urllib.request.OpenerDirector  # 取数通道类型，供调用方标注形参与返回值


def clean_opener() -> Opener:
    """忽略环境代理的取数通道"""
    # 空映射屏蔽 HTTP_PROXY、HTTPS_PROXY 与注册表发现，失效代理不会拖死本可直连的请求
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def proxied_opener(proxy_url: str) -> Opener:
    """显式走指定代理的取数通道"""
    pair = {"http": proxy_url, "https": proxy_url}
    return urllib.request.build_opener(urllib.request.ProxyHandler(pair))
