"""启动器侧取数通道

- 给出忽略环境代理的 opener
- 给出显式走指定代理的 opener
- 给出按通道取 JSON 的重发封装
"""

import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any

Opener = urllib.request.OpenerDirector  # 取数通道类型，供调用方标注形参与返回值

# 重发节奏
_RETRY_DELAY = 1.0  # 重发前的等待秒数
_MAX_ATTEMPTS = 3  # 含首发在内最多发三次


def clean_opener() -> Opener:
    """忽略环境代理的取数通道"""
    # 空映射屏蔽 HTTP_PROXY、HTTPS_PROXY 与注册表发现，失效代理不会拖死本可直连的请求
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def proxied_opener(proxy_url: str) -> Opener:
    """显式走指定代理的取数通道"""
    pair = {"http": proxy_url, "https": proxy_url}
    return urllib.request.build_opener(urllib.request.ProxyHandler(pair))


def fetch_json(
    url: str, opener: Opener, headers: dict[str, str], timeout: float
) -> Any:
    """按指定通道取一份 JSON 内容

    - 建连失败、超时或响应不是 JSON 即重发，次数用完交出 None
    """
    for attempt in range(_MAX_ATTEMPTS):
        if attempt:
            print(f"重试：{url}", file=sys.stderr)
            time.sleep(_RETRY_DELAY)
        try:
            request = urllib.request.Request(url, headers=headers)
            with opener.open(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError):
            continue

    return None
