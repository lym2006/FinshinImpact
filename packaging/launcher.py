# packaging/launcher.py
"""启动器（发布包的构建源）

- 首次启动自动安装嵌入式 Python、依赖与浏览器内核
- 启动前比对在线版本页，发现新版确认后整包升级，用户资产保留
"""

import ctypes
import hashlib
import os
import shutil
import subprocess
import sys
import time
import tomllib
import urllib.request
import webbrowser
import zipfile
from pathlib import Path

from packaging.version import Version

# ==================== 常量 ====================

APP_TITLE = "TelegramBot"
PAGES_PYPROJECT_URL = "https://lym2006.github.io/TelegramBot/pyproject.toml"
RELEASE_ZIP_URL = (
    "https://github.com/lym2006/TelegramBot/releases/download/v{ver}/TelegramBot-v{ver}.zip"
)
# 手动下载引导页：蓝奏云备用目录（访问密码随弹窗展示）
DOWNLOAD_PAGE_URL = "https://wwbgy.lanzoub.com/b0pnwooed"
DOWNLOAD_PASSWORD = "5rp0"
REQUEST_TIMEOUT = 10.0
DOWNLOAD_CHUNK = 65536

# 国内直连 GitHub 慢：官方源失败自动切换公共加速镜像
RELEASE_MIRRORS = ("https://gh-proxy.com/", "https://ghproxy.net/")
# pip 走清华源，官方源兜底；浏览器内核走 npmmirror
PIP_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple"
PIP_FALLBACK_URL = "https://pypi.org/simple"
PLAYWRIGHT_CDN = "https://cdn.npmmirror.com/binaries/playwright"

# 升级保留：用户资产、运行环境与启动器本体（Windows 锁运行中的 exe）
PRESERVE_NAMES = ("config.toml", "data", "logs", "runtime", "_update", "TelegramBot.exe", "_internal")

_MB_ICON_INFO = 0x40
_MB_ICON_ERROR = 0x10
_MB_YESNO = 0x04
_ID_YES = 6


# ==================== 弹窗反馈 ====================


def _info(text: str) -> None:
    """信息弹窗"""
    ctypes.windll.user32.MessageBoxW(0, text, APP_TITLE, _MB_ICON_INFO)


def _ask_yes_no(text: str) -> bool:
    """询问弹窗，返回用户是否选择「是」"""
    flags = _MB_YESNO | _MB_ICON_INFO
    return ctypes.windll.user32.MessageBoxW(0, text, APP_TITLE, flags) == _ID_YES


def _fail_exit(text: str) -> None:
    """错误弹窗并退出"""
    ctypes.windll.user32.MessageBoxW(0, text, APP_TITLE, _MB_ICON_ERROR)
    sys.exit(1)


# ==================== 进度控制台 ====================

_console_open = False


def _open_console() -> None:
    """分配控制台窗口展示安装/升级进度

    exe 以无控制台编译，标准输出为空；AllocConsole 后重开 CONOUT$
    让 print 流入新窗口，pip 等子进程继承句柄实时回显输出。
    """
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
    """注册表系统代理注入环境变量，安装下载随其走代理

    嵌入式安装期 config.toml 尚未生成，OS 层代理是唯一通道；
    开关未开则维持直连，pip 与 Playwright 子进程继承环境变量。
    """
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
            PAGES_PYPROJECT_URL, timeout=REQUEST_TIMEOUT
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


def _bootstrap_pip(runtime: Path) -> None:
    """引导安装 pip（已存在则跳过）"""
    if (runtime / "Lib" / "site-packages" / "pip").exists():
        return
    cmd = [
        runtime / "python.exe",
        runtime / "get-pip.py",
        "--no-warn-script-location",
    ]
    try:
        subprocess.run([*cmd, "--index-url", PIP_INDEX_URL], check=True)
    except subprocess.CalledProcessError:
        print("清华源不可用，回退 pip 官方源重试")
        subprocess.run([*cmd, "--index-url", PIP_FALLBACK_URL], check=True)


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
    try:
        subprocess.run(
            [*base, "--index-url", PIP_INDEX_URL, *deps], check=True
        )
    except subprocess.CalledProcessError:
        print("清华源不可用，回退 pip 官方源重试")
        subprocess.run(
            [*base, "--index-url", PIP_FALLBACK_URL, *deps], check=True
        )


def _install_browser(runtime: Path) -> None:
    """下载 Playwright 的 chromium 内核（装到用户目录，多程序共享）

    默认走 npmmirror 加速，失败清掉镜像变量回退官方源重试。
    """
    cmd = [runtime / "python.exe", "-m", "playwright", "install", "chromium"]
    env = os.environ.copy()
    env["PLAYWRIGHT_DOWNLOAD_HOST"] = PLAYWRIGHT_CDN
    try:
        subprocess.run(cmd, check=True, env=env)
    except subprocess.CalledProcessError:
        del env["PLAYWRIGHT_DOWNLOAD_HOST"]
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
    except subprocess.CalledProcessError as e:
        _fail_exit(f"环境安装失败：{e.cmd[-2]} {e.cmd[-1]}\n请检查网络后重新双击启动")
    except FileNotFoundError as e:
        _fail_exit(f"安装文件缺失：{e}\n发布包可能损坏，请重新下载")
    except zipfile.BadZipFile:
        _fail_exit("内嵌运行环境包损坏（发布物不完整）\n请到 Releases 页重新下载最新发布包")
    (runtime / ".installed").write_text(_deps_digest(deps))


# ==================== 自动升级 ====================


def _report_progress(done: int, total: int, start: float) -> None:
    """单行刷新下载进度：百分比、字节量与速率"""
    elapsed = max(time.monotonic() - start, 1e-6)
    speed = done / elapsed / 1048576
    if total:
        line = (
            f"\r  {done / total * 100:5.1f}%"
            f"  {done / 1048576:.1f}/{total / 1048576:.1f} MB"
            f"  {speed:.1f} MB/s        "
        )
    else:
        line = f"\r  已下载 {done / 1048576:.1f} MB  {speed:.1f} MB/s        "
    print(line, end="", flush=True)


def _download_one(url: str, target: Path) -> None:
    """单源下载并实时打印进度"""
    with urllib.request.urlopen(url, timeout=60.0) as resp:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        start = time.monotonic()
        with open(target, "wb") as f:
            while chunk := resp.read(DOWNLOAD_CHUNK):
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
            print(f"该源失败（{e}），尝试下一个")
    raise RuntimeError(f"全部下载源失败：{last_error}")


def _apply_update(root: Path, version: str) -> bool:
    """下载新版整包并覆盖源码，用户资产与启动器本体保留"""
    stage = root / "_update"
    try:
        print(f"下载 v{version} 发布物…")
        shutil.rmtree(stage, ignore_errors=True)
        stage.mkdir(parents=True)
        zip_url = RELEASE_ZIP_URL.format(ver=version)
        _fetch_zip(
            [zip_url, *(m + zip_url for m in RELEASE_MIRRORS)],
            stage / "package.zip",
        )
        with zipfile.ZipFile(stage / "package.zip") as zf:
            zf.extractall(stage)
        new_root = stage / "TelegramBot"
        if not new_root.exists():
            raise FileNotFoundError("发布包缺少 TelegramBot 顶层目录")
        print("应用更新（保留配置、数据与日志）…")
        for item in new_root.iterdir():
            if item.name in PRESERVE_NAMES:
                continue
            target = root / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)
        return True
    except Exception as e:
        print(f"升级失败：{e}")
        if _ask_yes_no(
            "自动升级失败，是否打开蓝奏云手动下载最新版？\n"
            f"访问密码：{DOWNLOAD_PASSWORD}，选择否则按当前版本启动。"
        ):
            webbrowser.open(DOWNLOAD_PAGE_URL)
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
    subprocess.Popen(
        [str(root / "runtime" / "pythonw.exe"), str(root / "main.py")],
        cwd=str(root),
    )


def main() -> None:
    """安装环境 → 检查升级 → 拉起主程序 → 回收进度窗口"""
    root = _root_dir()
    _apply_system_proxy()
    _ensure_runtime(root)
    _check_update(root)
    _launch(root)
    _close_console()


if __name__ == "__main__":
    main()
