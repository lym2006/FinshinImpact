# packaging/launcher.py
"""启动器（发布包的构建源）

- 首次启动自动安装嵌入式 Python、依赖与浏览器内核
- 启动前比对在线版本页，发现新版确认后整包升级，用户资产保留
- 启动器本体可随升级自动更换：新壳暂存包根，下次启动改名换入后重启
"""

import ctypes
import filecmp
import hashlib
import os
import shutil
import subprocess
import sys
import time
import tomllib
import urllib.request
import zipfile
from pathlib import Path

from packaging.version import Version

# ==================== 常量 ====================

_APP_TITLE = "TelegramBot"
_PAGES_PYPROJECT_URL = "https://lym2006.github.io/TelegramBot/pyproject.toml"
_RELEASE_ZIP_URL = "https://github.com/lym2006/TelegramBot/releases/download/v{ver}/TelegramBot-v{ver}.zip"

_REQUEST_TIMEOUT = 10.0  # 版本页请求超时 10 秒
_DOWNLOAD_CHUNK = 64 * 1024  # 分块粒度 64 KB（刷进度）
_DOWNLOAD_TIMEOUT = 60.0  # 发布物下载超时 60 秒
_BYTES_PER_MB = 1024 * 1024  # 1 MB
_SPEED_EPS = 1e-6  # 0.000001 秒下限，起步防除零

# 国内直连 GitHub 慢：公共加速镜像优先，官方源兜底
_RELEASE_MIRRORS = ("https://gh-proxy.com/", "https://ghproxy.net/")

# pip 索引按序重试：国内多源轮询，最后官方源兜底
_PIP_INDEX_URLS = (
    "https://pypi.tuna.tsinghua.edu.cn/simple",
    "https://mirrors.aliyun.com/pypi/simple",
    "https://mirrors.cloud.tencent.com/pypi/simple",
    "https://pypi.org/simple",
)
_PLAYWRIGHT_CDN = "https://cdn.npmmirror.com/binaries/playwright"

# 升级保留：用户资产与运行环境
# _internal 只装二进制依赖，启动器自身字节码在 exe 尾部，换壳无需动它
_PRESERVE_NAMES = ("config.toml", "data", "logs", "runtime", "_update", "_internal")

# 换壳：Windows 锁住运行中的 exe 不许覆盖，但允许整文件改名挪走；
# 因此升级时新壳先暂存，下次启动开头旧壳改名 .old、新壳原位放入并立即重启
_SHELL_EXE = "TelegramBot.exe"
_SHELL_PENDING = "_shell_update"
_SHELL_BAK_SUFFIX = ".old"

_MB_ICON_INFO = 0x40
_MB_ICON_ERROR = 0x10
_MB_YESNO = 0x04
_ID_YES = 6


# ==================== 弹窗反馈 ====================


def _info(text: str) -> None:
    """信息弹窗"""
    ctypes.windll.user32.MessageBoxW(0, text, _APP_TITLE, _MB_ICON_INFO)


def _ask_yes_no(text: str) -> bool:
    """询问弹窗，返回用户是否选择「是」"""
    flags = _MB_YESNO | _MB_ICON_INFO
    return ctypes.windll.user32.MessageBoxW(0, text, _APP_TITLE, flags) == _ID_YES


def _fail_exit(text: str) -> None:
    """错误弹窗并退出"""
    ctypes.windll.user32.MessageBoxW(0, text, _APP_TITLE, _MB_ICON_ERROR)
    sys.exit(1)


# ==================== 进度控制台 ====================

_console_open = False


def _open_console() -> None:
    """分配控制台窗口展示安装/升级进度"""
    global _console_open
    if _console_open:
        return
    ctypes.windll.kernel32.AllocConsole()
    sys.stdout = open("CONOUT$", "w", encoding="oem", errors="replace", buffering=1)
    sys.stderr = sys.stdout
    _console_open = True


def _close_console() -> None:
    """回收控制台窗口（主程序拉起后调用）"""
    global _console_open
    if not _console_open:
        return
    ctypes.windll.kernel32.FreeConsole()
    _console_open = False


# ==================== 系统代理透传 ====================


def _apply_system_proxy() -> None:
    """注册表系统代理注入环境变量，安装下载随其走代理"""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as key:
            if not winreg.QueryValueEx(key, "ProxyEnable")[0]:
                return
            raw = str(winreg.QueryValueEx(key, "ProxyServer")[0]).strip()
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
    # 仅供安装期的 pip/playwright 子进程继承，_launch 会剔除


# ==================== 版本与依赖（pyproject 单一来源） ====================


def _pyproject_data(root: Path) -> dict:
    """读取发布包内 pyproject 的解析结果"""
    with open(root / "pyproject.toml", "rb") as f:
        return tomllib.load(f)


def _local_version(root: Path) -> str:
    """本地版本号"""
    return str(_pyproject_data(root)["project"]["version"])


def _dependencies(root: Path) -> list[str]:
    """运行依赖清单：直接取 pyproject，不落中间文件"""
    return list(_pyproject_data(root)["project"]["dependencies"])


def _remote_version() -> str | None:
    """读取版本页的在线版本号，网络不通返回 None"""
    try:
        with urllib.request.urlopen(
            _PAGES_PYPROJECT_URL, timeout=_REQUEST_TIMEOUT
        ) as resp:
            data = tomllib.loads(resp.read().decode("utf-8"))
        return str(data["project"]["version"])
    except Exception:
        return None


# ==================== 环境安装 ====================


def _deps_digest(deps: list[str]) -> str:
    """依赖清单摘要：内容变动即触发重装"""
    return hashlib.sha256("\n".join(deps).encode("utf-8")).hexdigest()


def _installed_ok(runtime: Path, deps: list[str]) -> bool:
    """已装环境且依赖清单未变则免装"""
    stamp = runtime / ".installed"
    if not (runtime / "python.exe").exists() or not stamp.exists():
        return False
    return stamp.read_text() == _deps_digest(deps)


def _extract_embed(runtime: Path) -> None:
    """解压嵌入式 Python 到 runtime 目录"""
    with zipfile.ZipFile(runtime / "python-embed.zip") as zf:
        zf.extractall(runtime)


def _enable_site(runtime: Path) -> None:
    """放开嵌入式包的 site-packages（默认注释锁死，pip 装不进第三方包）"""
    pth = next(iter(runtime.glob("python*._pth")))
    text = pth.read_text()
    if "#import site" in text:
        pth.write_text(text.replace("#import site", "import site"))


def _pip_with_index_retry(cmd: list[str]) -> None:
    """按序尝试多镜像索引，失败换源重试直至耗尽"""
    for i, index in enumerate(_PIP_INDEX_URLS):
        if i:
            print(f"换源重试（第 {i + 1} 次）：{index}")
            print("上方报错无需处理，程序正在自动切换镜像源。\n\n")
        try:
            subprocess.run([*cmd, "--index-url", index], check=True)
            return
        except subprocess.CalledProcessError:
            print("\n\n")
            if i == len(_PIP_INDEX_URLS) - 1:
                raise


def _bootstrap_pip(runtime: Path) -> None:
    """引导安装 pip（已存在则跳过）"""
    if (runtime / "Lib" / "site-packages" / "pip").exists():
        return
    cmd = [
        runtime / "python.exe",
        runtime / "get-pip.py",
        "--no-warn-script-location",
    ]
    _pip_with_index_retry(cmd)


def _install_deps(runtime: Path, deps: list[str]) -> None:
    """把 pyproject 依赖清单直接交给 pip 安装"""
    base = [
        runtime / "python.exe",
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-warn-script-location",
    ]
    _pip_with_index_retry([*base, *deps])


def _install_browser(runtime: Path) -> None:
    """下载 Playwright 的 chromium 内核（装到用户目录，多程序共享）

    默认走 npmmirror 加速，失败清掉镜像变量回退官方源重试。
    """
    cmd = [runtime / "python.exe", "-m", "playwright", "install", "chromium"]
    env = os.environ.copy()
    env["PLAYWRIGHT_DOWNLOAD_HOST"] = _PLAYWRIGHT_CDN
    try:
        subprocess.run(cmd, check=True, env=env)
    except subprocess.CalledProcessError:
        print("\n\n")
        del env["PLAYWRIGHT_DOWNLOAD_HOST"]
        print("npmmirror 不可用，已回退官方源重试，上方报错无需处理。\n\n")
        subprocess.run(cmd, check=True, env=env)


def _ensure_runtime(root: Path) -> None:
    """补齐运行环境：嵌入式 Python → site 开关 → pip → 依赖 → 浏览器内核"""
    runtime = root / "runtime"
    deps = _dependencies(root)
    if _installed_ok(runtime, deps):
        return
    _info("首次运行需要安装运行环境，期间保持网络畅通，可能需要几分钟。")
    _open_console()
    try:
        print("[1/5] 解压嵌入式 Python…")
        if not (runtime / "python.exe").exists():
            _extract_embed(runtime)
        print("[2/5] 放开 site-packages…")
        _enable_site(runtime)
        print("[3/5] 安装 pip…")
        _bootstrap_pip(runtime)
        print("[4/5] 安装依赖（下方为 pip 实时输出，约几分钟）…")
        _install_deps(runtime, deps)
        print("[5/5] 下载浏览器内核…")
        _install_browser(runtime)
        print("环境安装完成，即将启动主程序")
    except subprocess.CalledProcessError:
        _fail_exit("依赖安装失败，请查看进度窗口末尾输出\n恢复网络后重新双击即可续装")
    except FileNotFoundError as e:
        _fail_exit(f"安装文件缺失：{e}\n发布包可能损坏，请重新下载")
    except zipfile.BadZipFile:
        _fail_exit(
            "内嵌运行环境包损坏（发布物不完整）\n请到 Releases 页重新下载最新发布包"
        )
    (runtime / ".installed").write_text(_deps_digest(deps))


# ==================== 自动升级 ====================


def _report_progress(done: int, total: int, start: float) -> None:
    """单行刷新下载进度：百分比、字节量与速率"""
    elapsed = max(time.monotonic() - start, _SPEED_EPS)
    speed = done / elapsed / _BYTES_PER_MB
    if total:
        line = (
            f"\r  {done / total * 100:5.1f}%"
            f"  {done / _BYTES_PER_MB:.1f}/{total / _BYTES_PER_MB:.1f} MB"
            f"  {speed:.1f} MB/s        "
        )
    else:
        line = f"\r  已下载 {done / _BYTES_PER_MB:.1f} MB  {speed:.1f} MB/s        "
    print(line, end="", flush=True)


def _download_one(url: str, target: Path) -> None:
    """单源下载并实时打印进度"""
    with urllib.request.urlopen(url, timeout=_DOWNLOAD_TIMEOUT) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        start = time.monotonic()
        with open(target, "wb") as f:
            while chunk := resp.read(_DOWNLOAD_CHUNK):
                f.write(chunk)
                done += len(chunk)
                _report_progress(done, total, start)
    print()


def _fetch_zip(urls: list[str], target: Path) -> None:
    """多源下载发布物：每源完成后校验 zip，坏包自动换源"""
    last_error: Exception | None = None
    for url in urls:
        try:
            print(f"下载 {url}")
            _download_one(url, target)
            if zipfile.is_zipfile(target):
                return
            raise zipfile.BadZipFile("下载内容不是有效 zip")
        except Exception as e:
            last_error = e
            print(f"该源失败（{e}），已自动切换下一个源，上方报错无需处理。\n\n")
    raise RuntimeError(f"全部下载源失败：{last_error}")


def _apply_update(root: Path, version: str) -> bool:
    """整包升级

    下载新版并覆盖源码，用户资产保留；新壳有变化则暂存包根，
    待下次启动换入。
    """
    stage = root / "_update"
    try:
        # 下载：镜像源优先、官方源兜底，zip 校验通过才继续
        print(f"下载 v{version} 发布物…")
        shutil.rmtree(stage, ignore_errors=True)
        stage.mkdir(parents=True)
        zip_url = _RELEASE_ZIP_URL.format(ver=version)
        _fetch_zip(
            [*(m + zip_url for m in _RELEASE_MIRRORS), zip_url],
            stage / "package.zip",
        )
        with zipfile.ZipFile(stage / "package.zip") as zf:
            zf.extractall(stage)
        # 解压：暂存目录展开，校验顶层结构
        new_root = stage / "TelegramBot"
        if not new_root.exists():
            raise FileNotFoundError("发布包缺少 TelegramBot 顶层目录")
        # 覆盖：白名单外目录整树拷、文件逐个拷；本体走暂存不许直接覆盖
        print("应用更新（保留配置、数据与日志）…")
        for item in new_root.iterdir():
            if item.name in _PRESERVE_NAMES or item.name == _SHELL_EXE:
                continue
            target = root / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)
        # 换壳：新 exe 与当前不同则暂存包根，下次启动开头换入
        new_exe = new_root / _SHELL_EXE
        if new_exe.is_file() and not filecmp.cmp(new_exe, root / _SHELL_EXE, shallow=False):
            shutil.rmtree(root / _SHELL_PENDING, ignore_errors=True)
            (root / _SHELL_PENDING).mkdir()
            shutil.copy2(new_exe, root / _SHELL_PENDING / _SHELL_EXE)
            print("新启动器已暂存，下次启动自动更换")
        return True
    except Exception as e:
        print(f"升级失败：{e}\n按当前版本启动，可稍后重试或到 Releases 页手动下载")
        return False
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def _check_update(root: Path) -> None:
    """版本比对与确认后升级；网络不通静默跳过（GUI 内可手动检查）"""
    local = _local_version(root)
    remote = _remote_version()
    if remote is None or Version(remote) <= Version(local):
        return
    if not _ask_yes_no(
        f"发现新版本 v{remote}（当前 v{local}），立即升级？\n选择否则按当前版本启动。"
    ):
        return
    _open_console()
    print(f"发现新版本 v{remote}（当前 v{local}），开始升级…")
    if _apply_update(root, remote):
        # 依赖清单已随包更新：重走安装检查，仅补装变动部分
        _ensure_runtime(root)
        print(f"已升级到 v{remote}")
        _info(f"已升级到 v{remote}")


# ==================== 主流程 ====================


def _apply_shell_update(root: Path) -> None:
    """启动器换壳

    旧 exe 改名让位，暂存的新壳放入原位后立即重启。
    自我改名后本进程句柄仍跟着旧文件走，原位放入新壳重启即完成更换。
    """
    pending = root / _SHELL_PENDING
    new_exe = pending / _SHELL_EXE
    if not new_exe.is_file():
        return
    old_exe = root / _SHELL_EXE
    bak = old_exe.with_name(_SHELL_EXE + _SHELL_BAK_SUFFIX)
    try:
        bak.unlink(missing_ok=True)
    except OSError:
        pass  # 上次遗留的备份仍被占用：改名会失败，走下面的放弃分支
    try:
        old_exe.rename(bak)  # 旧 exe 变身 .old 让位
    except OSError:
        # 改名失败多半是被安全软件短暂占用：放弃本次更换，保留暂存下次再试
        print("启动器暂被占用，本次沿用旧版继续")
        return
    shutil.move(str(new_exe), str(old_exe))
    shutil.rmtree(pending, ignore_errors=True)
    subprocess.Popen([str(old_exe)], cwd=str(root))  # 拉起新壳
    sys.exit(0)


def _root_dir() -> Path:
    """发布包根目录：启动器 exe 位于包根"""
    if not getattr(sys, "frozen", False):
        _fail_exit("本文件需经 build.py 编译成 exe 后使用")
    return Path(sys.executable).resolve().parent


def _launch(root: Path) -> None:
    """以无窗口解释器拉起主程序入口脚本

    main.py 位于包根，注入源码路径后等价 python -m bot，
    显式入口便于调试：可直接运行 main.py 复现问题。
    """
    # 剔除安装期注入的代理变量：主程序有自己的三级解析，不该被 OS 代理绑架
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("HTTP_PROXY", "HTTPS_PROXY")
    }
    subprocess.Popen(
        [str(root / "runtime" / "pythonw.exe"), str(root / "main.py")],
        cwd=str(root),
        env=env,
    )


def main() -> None:
    """换壳 → 安装环境 → 检查升级 → 拉起主程序 → 回收进度窗口"""
    root = _root_dir()
    _apply_shell_update(root)
    _apply_system_proxy()
    _ensure_runtime(root)
    _check_update(root)
    _launch(root)
    _close_console()


if __name__ == "__main__":
    main()
