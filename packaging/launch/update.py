# packaging/launch/update.py
"""发布物整包升级

- 比对在线版本页，确认后下载新版并覆盖源码，用户资产保留
- 升级前可先看远程 release 正文
- 多源带进度下载，坏包自动换源
- 升级收尾当场换入新壳并拉起
"""

import filecmp
import shutil
import sys
import time
import zipfile
from pathlib import Path

import netio
from pack_spec import (
    APP_NAME,
    HDR_CONTENT_LENGTH,
    PRESERVE_NAMES,
    RELEASE_MIRRORS,
    RELEASE_ZIP_URL,
    SHELL_EXE,
    SHELL_PENDING,
    local_version,
    remote_release_notes,
    remote_version,
)
from packaging.version import Version

from . import console, dialogs, proxy, runtime, shell

# 分块粒度 64 KB（刷进度）
_DOWNLOAD_CHUNK = 64 * 1024
_DOWNLOAD_TIMEOUT = 20.0  # 建连与单块读取超时 20 秒
_BYTES_PER_MB = 1024 * 1024  # 1 MB
_BYTES_PER_KB = 1024  # 1 KB
_SPEED_EPS = 1e-6  # 1 微秒下限，起步防除零


def check_update(root: Path) -> None:
    """升级检查

    - 网络不通静默跳过
    - GUI 内可手动检查
    - 升级前可先看本次变化
    """
    local = local_version(root)
    remote = remote_version(proxy.system_proxy_url())
    if remote is None or Version(remote) <= Version(local):
        return
    new_msg = f"新版本可用 v{local} -> v{remote}"
    if not _ask_upgrade(new_msg, remote):
        return
    console.open_console()
    print(f"{new_msg}，开始升级…")
    if not _apply_update(root, remote):
        if not dialogs.ask_yes_no(
            "升级失败，详情见进度窗口。\n仍以当前版本启动？选否则退出程序。"
        ):
            sys.exit(1)
        return

    # 依赖清单已随包更新：重走安装检查，仅补装变动部分
    runtime.ensure_runtime(root)
    print(f"已升级到 v{remote}")
    dialogs.info(f"已升级到 v{remote}")

    # 新壳当场换入并拉起，主程序抢锁后旧壳退场，用户无需关闭再打开
    shell.apply_shell_update(root, handoff=True)


def _ask_upgrade(new_msg: str, version: str) -> bool:
    """确认是否立即升级

    - 选否先看本次变化，看完再问一次
    """
    answer = dialogs.ask_yes_no_cancel(
        f"{new_msg}，立即升级？\n选是立即升级，选否先看本次变化，选取消按当前版本启动。"
    )
    if answer is dialogs.Answer.CANCEL:
        return False
    if answer is dialogs.Answer.YES:
        return True

    console.open_console()
    _print_changes(version)
    return dialogs.ask_yes_no(f"{new_msg}，立即升级？\n选择否则按当前版本启动。")


def _print_changes(version: str) -> None:
    """打印指定版本的版本变化正文"""
def _print_changes(version: str) -> None:
    """打印指定版本的版本变化正文"""
    notes = remote_release_notes(version, proxy.system_proxy_url())
    if not notes:
        print(f"未取到 v{version} 的发布说明，详情见 GitHub Releases 页")
        console.hold_console()
        return
    print(notes)
    console.hold_console(f"以上为 v{version} 的变化内容，按回车继续…")


def _apply_update(root: Path, version: str) -> bool:
    """整包升级

    - 下载新版并覆盖源码，用户资产保留
    - 启动器有变化则暂存包根，升级收尾时换入
    """
    stage = root / "_update"
    try:
        # 下载：镜像源优先、官方源兜底，zip 校验通过才继续
        print(f"下载 v{version} 发布物…")
        shutil.rmtree(stage, ignore_errors=True)
        stage.mkdir(parents=True)
        zip_url = RELEASE_ZIP_URL.format(ver=version)
        urls = [*(m + zip_url for m in RELEASE_MIRRORS), zip_url]
        _fetch_zip(urls, stage / "package.zip")
        with zipfile.ZipFile(stage / "package.zip") as zf:
            zf.extractall(stage)

        # 解压：暂存目录展开，校验顶层结构
        new_root = stage / APP_NAME
        if not new_root.exists():
            raise FileNotFoundError("发布包缺少 FinshinImpact 顶层目录")

        # 覆盖：白名单外目录整树先删后拷、文件逐个拷，本体走暂存不许直接覆盖
        print("应用更新（保留配置、数据与日志）…")
        for item in new_root.iterdir():
            if item.name in PRESERVE_NAMES or item.name == SHELL_EXE:
                continue
            target = root / item.name
            if item.is_dir():
                # 先删后拷：只合并会残留新版已删除的旧代码，遮蔽同名新模块致启动即崩
                shutil.rmtree(target, ignore_errors=True)
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)

        # 换壳：新 exe 与当前不同则暂存包根，升级收尾当场换入
        new_exe = new_root / SHELL_EXE
        if new_exe.is_file() and not filecmp.cmp(
            new_exe, root / SHELL_EXE, shallow=False
        ):
            shutil.rmtree(root / SHELL_PENDING, ignore_errors=True)
            (root / SHELL_PENDING).mkdir()
            shutil.copy2(new_exe, root / SHELL_PENDING / SHELL_EXE)
        return True
    except Exception as e:
        print(f"升级失败：{e}")
        console.hold_console()
        return False
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def _report_progress(done: int, total: int, start: float) -> None:
    """单行刷新下载进度

    - 含百分比、字节量与速率
    - 速率低于 1 MB/s 改用 KB/s
    """
    elapsed = max(time.monotonic() - start, _SPEED_EPS)
    bps = done / elapsed
    if bps < _BYTES_PER_MB:
        speed = f"{bps / _BYTES_PER_KB:.0f} KB/s"
    else:
        speed = f"{bps / _BYTES_PER_MB:.1f} MB/s"
    if total:
        line = (
            f"\r  {done / total * 100:5.1f}%"
            f"  {done / _BYTES_PER_MB:.1f}/{total / _BYTES_PER_MB:.1f} MB"
            f"  {speed}        "
        )
    else:
        line = f"\r  已下载 {done / _BYTES_PER_MB:.1f} MB  {speed}        "
    print(line, end="", flush=True)


def _download_one(url: str, target: Path, opener: netio.Opener) -> None:
    """单源下载并实时打印进度"""
    with opener.open(url, timeout=_DOWNLOAD_TIMEOUT) as resp:
        total = int(resp.headers.get(HDR_CONTENT_LENGTH) or 0)
        done = 0
        start = time.monotonic()
        with open(target, "wb") as f:
            while chunk := resp.read(_DOWNLOAD_CHUNK):
                f.write(chunk)
                done += len(chunk)
                _report_progress(done, total, start)
    print()


def _download_pass(
    urls: list[str], target: Path, opener: netio.Opener
) -> Exception | None:
    """一轮多源下载，全成返回 None，否则返回末次失败原因"""
    last_error: Exception | None = None
    for url in urls:
        try:
            print(f"下载 {url}")
            _download_one(url, target, opener)
            if zipfile.is_zipfile(target):
                return None
            raise zipfile.BadZipFile("下载内容不是有效 zip")
        except Exception as e:
            last_error = e
            print(f"该源失败（{e}），已自动切换下一个源，上方报错无需处理。\n\n")
    return last_error


def _fetch_zip(urls: list[str], target: Path) -> None:
    """多源下载发布物

    - 每源完成后校验 zip，坏包自动换源
    - 干净直连全源失败后，带注册表系统代理再走一轮
    """
    openers = [netio.clean_opener()]
    proxy_url = proxy.system_proxy_url()
    if proxy_url:
        openers.append(netio.proxied_opener(proxy_url))
    last_error: Exception | None = None
    for opener in openers:
        last_error = _download_pass(urls, target, opener)
        if last_error is None:
            return
    raise RuntimeError(f"全部下载源失败：{last_error}")
