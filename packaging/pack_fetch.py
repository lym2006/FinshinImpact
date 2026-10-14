# packaging/pack_fetch.py
"""构建原料下载

- 嵌入式 Python 与 uv 安装包多源下载并落 dist 缓存
- zip 条目校验，uv 包加 sha256 比对，坏包自动换源
"""

import hashlib
import shutil
import urllib.request
import zipfile
from pathlib import Path

from pack_spec import CACHE

# 构建原料下载源：镜像优先、官方兜底
_EMBED_VERSION = "3.11.9"
_EMBED_FILE = f"python-{_EMBED_VERSION}-embed-amd64.zip"
_EMBED_URL_SUFFIX = f"python/{_EMBED_VERSION}/{_EMBED_FILE}"
_EMBED_URLS = (
    f"https://registry.npmmirror.com/-/binary/{_EMBED_URL_SUFFIX}",
    f"https://mirrors.huaweicloud.com/{_EMBED_URL_SUFFIX}",
    f"https://npmmirror.com/mirrors/{_EMBED_URL_SUFFIX}",
    f"https://www.python.org/ftp/{_EMBED_URL_SUFFIX}",
)

# uv 随包下发给启动器装依赖，取用方在启动器的 payload 解包
_UV_VERSION = "0.12.23"
_UV_URL_SUFFIX = (
    f"astral-sh/uv/releases/download/{_UV_VERSION}/uv-x86_64-pc-windows-msvc.zip"
)
_UV_URLS = (
    f"https://gh-proxy.com/https://github.com/{_UV_URL_SUFFIX}",
    f"https://ghproxy.net/https://github.com/{_UV_URL_SUFFIX}",
    f"https://github.com/{_UV_URL_SUFFIX}",
)
_UV_CACHE_NAME = f"uv-{_UV_VERSION}.zip"

# 官方发布页校验值，升 _UV_VERSION 必须同步换值
_UV_SHA256 = "75d05de6762778c31ee183398de7dd15093fad0ed90b1f236d8205ea5ec00c90"

_DOWNLOAD_TIMEOUT = 120.0  # 构建原料下载超时 120 秒（2 分钟）


def fetch_embed() -> Path:
    """取用嵌入式 Python 原料"""
    return _fetch_to_cache(list(_EMBED_URLS), _EMBED_FILE)


def fetch_uv() -> Path:
    """取用 uv 安装包原料"""
    return _fetch_to_cache(list(_UV_URLS), _UV_CACHE_NAME, _UV_SHA256)


def _download(url: str, target: Path) -> None:
    """下载文件到指定路径

    - 先写 .part 临时名，成功后改名落盘
    """
    print(f"下载 {url}")
    part = target.with_name(target.name + ".part")
    try:
        with (
            urllib.request.urlopen(url, timeout=_DOWNLOAD_TIMEOUT) as resp,
            open(part, "wb") as f,
        ):
            shutil.copyfileobj(resp, f)
        part.replace(target)
    except Exception:
        # 中断的半截文件不许以正式名存在，失败即清残留
        part.unlink(missing_ok=True)
        raise


def _download_verified(urls: list[str], target: Path, sha256: str = "") -> None:
    """构建原料多源下载

    - zip 验条目，带哈希的再比对 sha256，任一不过即该源失败换下一源
    """
    last_error: Exception | None = None
    for url in urls:
        try:
            _download(url, target)
            with zipfile.ZipFile(target) as zf:
                if zf.testzip() is not None:
                    raise zipfile.BadZipFile("zip 条目校验失败")
            if sha256:
                digest = hashlib.sha256(target.read_bytes()).hexdigest()
                if digest != sha256:
                    raise ValueError(f"sha256 不符：{digest}")
            return
        except Exception as e:
            last_error = e
            print(f"该源失败（{e}），尝试下一个")
    target.unlink(missing_ok=True)
    raise RuntimeError(f"全部下载源均失败，中止构建：{last_error}")


def _fetch_to_cache(urls: list[str], name: str, sha256: str = "") -> Path:
    """构建原料取用缓存

    - 原料跨构建复用
    - 清 dist 目录即清缓存
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / name
    if cached.exists():
        print(f"命中缓存 {name}")
        return cached
    _download_verified(urls, cached, sha256)
    return cached
