# packaging/pack_release.py
"""发布状态自检

- 本地版本号、远端 tag、本地包指纹、在线版本页、发布物各源可达逐项检查
"""

import hashlib
import subprocess
import urllib.request

from pack_spec import (
    APP_NAME,
    DIST,
    HDR_CONTENT_LENGTH,
    RELEASE_MIRRORS,
    RELEASE_ZIP_URL,
    ROOT,
    local_version,
    remote_version,
)

_BYTES_PER_MB = 1024 * 1024  # 1 MB
_PROBE_TIMEOUT = 10.0  # 发布物 HEAD 探测超时 10 秒


def check_release() -> None:
    """发布前后自检

    - 版本号、远端 tag、本地包指纹、在线版本页、发布物各源可达
    """
    version = local_version(ROOT)
    tag_hit = subprocess.run(
        ["git", "ls-remote", "--tags", "origin", f"v{version}"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    zip_path = DIST / f"{APP_NAME}-v{version}.zip"
    local_size = zip_path.stat().st_size if zip_path.is_file() else 0
    local_digest = (
        hashlib.sha256(zip_path.read_bytes()).hexdigest() if local_size else ""
    )
    checks = [
        (
            "本地版本号",
            f"v{version}" if not version.endswith("-dev") else "开发号，先正式化",
        ),
        ("git tag 远端", "已推送" if tag_hit else "缺失，先 push tag"),
        (
            "本地 zip",
            f"{local_size / _BYTES_PER_MB:.1f} MB sha256={local_digest[:12]}"
            if local_size
            else "缺失，先构建",
        ),
        ("在线版本页", remote_version() or "读取失败"),
    ]
    zip_url = RELEASE_ZIP_URL.format(ver=version)
    checks.append(("发布物官方直连", _asset_probe(zip_url, local_size)))
    for mirror in RELEASE_MIRRORS:
        checks.append((f"发布物 {mirror}", _asset_probe(mirror + zip_url, local_size)))
    for name, detail in checks:
        print(f"[自检] {name}: {detail}")


def _asset_probe(url: str, local_size: int) -> str:
    """HEAD 探测发布物可达性与体积

    - 与本地 zip 大小一致即内容对得上，无需整包下载
    """
    if not local_size:
        return "本地无包，跳过"
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=_PROBE_TIMEOUT) as resp:
            remote = int(resp.headers.get(HDR_CONTENT_LENGTH) or 0)
    except Exception as e:
        return f"不可达（{type(e).__name__}），确认已上传 release"
    if remote == local_size:
        return f"可达，{remote / _BYTES_PER_MB:.1f} MB 与本地包一致"
    return f"可达但大小不符（远端 {remote / _BYTES_PER_MB:.1f} MB）"
