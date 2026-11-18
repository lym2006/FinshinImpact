"""启动器与构建侧取数通道

- 通道清单给到忽略环境代理的干净直连
- 取 JSON、取字节、探长度三种交出内容或空值，落盘下载一种交出末次异常
- 每条通道按同一节奏最多发三次，含首发
"""

import json
import shutil
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

Opener = urllib.request.OpenerDirector  # 取数通道类型，供调用方标注形参与返回值

# 重发节奏
_RETRY_DELAY = 1.0  # 重发前的等待秒数
_MAX_ATTEMPTS = 3  # 含首发在内最多发三次

# 落盘件的中转名后缀，写完才改成正式名
_PART_SUFFIX = ".part"


def _clean_opener() -> Opener:
    """忽略环境代理的取数通道"""
    # 空映射屏蔽 HTTP_PROXY、HTTPS_PROXY 与注册表发现，失效代理不会拖死本可直连的请求
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def openers() -> list[Opener]:
    """排出干净直连的取数通道清单"""
    return [_clean_opener()]


def fetch_json(
    url: str, opener_list: Sequence[Opener], headers: dict[str, str], timeout: float
) -> Any:
    """按通道取一份 JSON 内容，全通道发完仍坏交出 None"""
    return _take(url, opener_list, lambda opener: _json(opener, url, headers, timeout))[
        0
    ]


def fetch_bytes(
    url: str, opener_list: Sequence[Opener], headers: dict[str, str], timeout: float
) -> bytes | None:
    """按通道取一份二进制内容，全通道发完仍坏交出 None"""
    return _take(url, opener_list, lambda opener: _body(opener, url, headers, timeout))[
        0
    ]


def probe_size(
    url: str, opener_list: Sequence[Opener], header: str, timeout: float
) -> tuple[int, str]:
    """按通道探一份远端内容声明的字节数

    - 交出字节数与末次失败说明，探通即说明是空串
    - 头名由调用方给，请求头名单源在声明那份文件里
    """
    size, note = _take(
        url, opener_list, lambda opener: _size(opener, url, header, timeout)
    )

    return int(size or 0), note


def download_to(
    url: str, opener_list: Sequence[Opener], target: Path, timeout: float
) -> None:
    """按通道把一份内容流式写到指定路径

    - 先写 .part 再改成正式名，坏件不留正式名
    - 全通道发完仍坏即交出末次失败说明
    """
    note = _take(url, opener_list, lambda opener: _write(opener, url, target, timeout))[
        1
    ]
    if note:
        raise RuntimeError(f"取不到 {url}：{note}")


def _take(
    url: str, opener_list: Sequence[Opener], grab: Callable[[Opener], Any]
) -> tuple[Any, str]:
    """逐条通道按同一节奏发，交出首次取到的值与末次失败说明

    - grab 交出 None 即这一发没取到内容
    - 失败说明点名到异常类型，没坏过即空串
    """
    note = ""
    for opener in opener_list:
        for attempt in range(_MAX_ATTEMPTS):
            if attempt:
                print(f"重试：{url}", file=sys.stderr)
                time.sleep(_RETRY_DELAY)
            try:
                found = grab(opener)
            except (urllib.error.URLError, OSError, ValueError) as error:
                note = f"{type(error).__name__}: {error}"
                continue
            if found is not None:
                return found, ""

    return None, note


def _body(
    opener: Opener, url: str, headers: dict[str, str], timeout: float
) -> bytes | None:
    """发一次 GET 取回正文，没取到交出 None"""
    request = urllib.request.Request(url, headers=headers)
    with opener.open(request, timeout=timeout) as response:
        body = response.read()

    return body or None


def _json(opener: Opener, url: str, headers: dict[str, str], timeout: float) -> Any:
    """发一次请求读一份 JSON，读不出交出 None"""
    body = _body(opener, url, headers, timeout)
    if body is None:
        return None

    return json.loads(body.decode("utf-8"))


def _size(opener: Opener, url: str, header: str, timeout: float) -> int:
    """发一次 HEAD 取响应头声明的字节数，取不到交出 0"""
    request = urllib.request.Request(url, method="HEAD")
    with opener.open(request, timeout=timeout) as response:
        return int(response.headers.get(header) or 0)


def _write(opener: Opener, url: str, target: Path, timeout: float) -> bool:
    """把一份响应流写进 .part，改成正式名即成了

    - 任何一种坏都先清掉半截件再把异常递出去
    """
    part = target.with_name(target.name + _PART_SUFFIX)
    try:
        with (
            opener.open(url, timeout=timeout) as response,
            open(part, "wb") as handle,
        ):
            shutil.copyfileobj(response, handle)
        part.replace(target)
    except Exception:
        part.unlink(missing_ok=True)
        raise

    return True
