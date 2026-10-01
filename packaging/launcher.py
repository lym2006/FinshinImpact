# packaging/launcher.py
"""发布包启动器

- 首次启动自动安装嵌入式 Python、依赖与浏览器内核
- 启动前比对在线版本页，发现新版确认后整包升级，用户资产保留
- 启动器本体随升级自动更换：当场换入并拉起新壳，主程序抢锁确认后旧壳退场
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
from ctypes import wintypes
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
_SPEED_EPS = 1e-6  # 1 微秒下限，起步防除零

# 国内直连 GitHub 慢：公共加速镜像优先，官方源兜底
_RELEASE_MIRRORS = ("https://gh-proxy.com/", "https://ghproxy.net/")

# pip 索引按序重试：国内多源轮询，最后官方源兜底
_PIP_INDEX_URLS = (
    "https://mirrors.aliyun.com/pypi/simple",
    "https://mirrors.cloud.tencent.com/pypi/simple",
    "https://pypi.tuna.tsinghua.edu.cn/simple",
    "https://pypi.org/simple",
)
_PLAYWRIGHT_CDN = "https://cdn.npmmirror.com/binaries/playwright"

# 升级保留用户资产（_internal 只装二进制依赖，换壳无需动）
_PRESERVE_NAMES = ("config.toml", "data", "logs", "runtime", "_update", "_internal")

# 换壳：运行中的 exe 不许覆盖但可改名，新壳先暂存、择机换入重启
_SHELL_EXE = "TelegramBot.exe"
_SHELL_PENDING = "_shell_update"
_SHELL_BAK_SUFFIX = ".old"

# 与 GUI icon.py 是同一份约定，两处改名必须同步：任务栏身份锚定到壳 exe 路径
_AUMID_ANCHOR_VAR = "TELEGRAMBOT_EXE_PATH"

_MB_ICON_INFO = 0x40
_MB_ICON_ERROR = 0x10
_MB_YESNO = 0x04
_ID_YES = 6
_DETACHED_PROCESS = 0x00000008  # 新壳不继承旧进度窗口，换壳无闪窗
_CREATE_NO_WINDOW = 0x08000000  # 后台命令不弹控制台窗口
_ICON_REFRESH_TIMEOUT = 5.0  # 图标缓存刷新超时 5 秒
_SWAP_FAST_TIMEOUT = 5.0  # 快交接静默等待上限 5 秒
_SWAP_SOOTHE_MS = 20_000  # 慢路径安抚弹窗驻留 20 秒
_HANDOFF_POLL_TICK = 0.5  # 抢锁轮询间隔 0.5 秒

# 与主程序 _single_instance 是同一把锁，两处改名必须同步
_MUTEX_NAME = "Local\\TelegramBot-Instance"
_ERROR_ALREADY_EXISTS = 183
_CreateMutexW = ctypes.windll.kernel32.CreateMutexW
_CreateMutexW.restype = wintypes.HANDLE  # 缺省 int 会在 64 位截断句柄
_CloseHandle = ctypes.windll.kernel32.CloseHandle
_MessageBoxTimeoutW = ctypes.windll.user32.MessageBoxTimeoutW


# ==================== 弹窗反馈 ====================


def _info(text: str) -> None:
    """信息弹窗"""
    ctypes.windll.user32.MessageBoxW(0, text, _APP_TITLE, _MB_ICON_INFO)


def _wait_info(text: str, ms: int) -> None:
    """限时信息弹窗"""
    _MessageBoxTimeoutW(0, text, _APP_TITLE, _MB_ICON_INFO, ms, 0)


def _instance_taken() -> bool:
    """实例锁占用静默探测"""
    # 持有锁则表明换壳成功
    handle = _CreateMutexW(None, False, _MUTEX_NAME)
    if not handle:
        return False
    busy = ctypes.GetLastError() == _ERROR_ALREADY_EXISTS
    _CloseHandle(handle)
    return busy


def _already_running() -> bool:
    """运行中提示

    - 实例锁已被占用则提示并退出
    """
    # 只探测不持有，真正的持锁者是随后拉起的主程序
    busy = _instance_taken()
    if busy:
        _info("机器人已在运行，请勿重复启动。\n请先关闭已开的窗口。")
    return busy


def _ask_yes_no(text: str) -> bool:
    """询问弹窗"""
    flags = _MB_YESNO | _MB_ICON_INFO
    return ctypes.windll.user32.MessageBoxW(0, text, _APP_TITLE, flags) == _ID_YES


def _fail_exit(text: str) -> None:
    """错误弹窗并退出"""
    ctypes.windll.user32.MessageBoxW(0, text, _APP_TITLE, _MB_ICON_ERROR)
    sys.exit(1)


# ==================== 进度控制台 ====================

_console_open = False


def _open_console() -> None:
    """分配控制台窗口

    - 展示安装/升级进度
    """
    global _console_open
    if _console_open:
        return
    ctypes.windll.kernel32.AllocConsole()
    sys.stdout = open("CONOUT$", "w", encoding="oem", errors="replace", buffering=1)
    sys.stderr = sys.stdout
    _console_open = True


def _close_console() -> None:
    """回收控制台窗口

    - 主程序拉起后回收窗口
    """
    global _console_open
    if not _console_open:
        return
    ctypes.windll.kernel32.FreeConsole()
    _console_open = False


def _hold_console() -> None:
    """驻留进度窗口

    - 供查阅失败详情
    """
    print("\n以上为失败详情，按回车继续…")
    try:
        with open("CONIN$", encoding="oem", errors="replace") as f:
            f.readline()
    except OSError:
        # 输入不可用多半无人值守，直接放行防卡死
        pass


# ==================== 系统代理透传 ====================


def _apply_system_proxy() -> None:
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
    """获取运行依赖清单"""
    return list(_pyproject_data(root)["project"]["dependencies"])


def _remote_version() -> str | None:
    """读取版本页在线版本号"""
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
    """依赖清单摘要

    - 内容变动即触发重装
    """
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
    """放开嵌入式包的 site-packages

    - 默认被注释锁死，pip 装不进第三方包
    """
    pth = next(iter(runtime.glob("python*._pth")))
    text = pth.read_text()
    if "#import site" in text:
        pth.write_text(text.replace("#import site", "import site"))


def _pip_with_index_retry(cmd: list[str]) -> None:
    """按序尝试多镜像索引

    - 失败换源重试直至耗尽
    """
    for i, index in enumerate(_PIP_INDEX_URLS):
        if i:
            print(f"换源重试（第 {i} 次）：{index}")
            print("上方报错无需处理，程序正在自动切换镜像源。\n\n")
        try:
            subprocess.run([*cmd, "--index-url", index], check=True)
            return
        except subprocess.CalledProcessError:
            print("\n\n")
            if i == len(_PIP_INDEX_URLS) - 1:
                raise


def _bootstrap_pip(runtime: Path) -> None:
    """引导安装 pip"""
    if (runtime / "Lib" / "site-packages" / "pip").exists():
        return
    cmd = [
        runtime / "python.exe",
        runtime / "get-pip.py",
        "--no-warn-script-location",
    ]
    _pip_with_index_retry(cmd)


def _install_deps(runtime: Path, deps: list[str]) -> None:
    """安装依赖清单"""
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
    """下载 Playwright 的 chromium 内核

    - 装到用户目录，多程序共享
    - 默认走 npmmirror 加速
    """
    cmd = [runtime / "python.exe", "-m", "playwright", "install", "chromium"]
    env = os.environ.copy()
    env["PLAYWRIGHT_DOWNLOAD_HOST"] = _PLAYWRIGHT_CDN
    try:
        subprocess.run(cmd, check=True, env=env)
    except subprocess.CalledProcessError:
        # 镜像不可用时清掉变量，回退官方源重试
        print("\n\n")
        del env["PLAYWRIGHT_DOWNLOAD_HOST"]
        print("npmmirror 不可用，已回退官方源重试，上方报错无需处理。\n\n")
        subprocess.run(cmd, check=True, env=env)


def _ensure_runtime(root: Path) -> None:
    """补齐运行环境

    - 嵌入式 Python → site 开关 → pip → 依赖 → 浏览器内核
    """
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
    """单行刷新下载进度

    - 含百分比、字节量与速率
    """
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
    """多源下载发布物

    - 每源完成后校验 zip，坏包自动换源
    """
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

    - 下载新版并覆盖源码，用户资产保留
    - 新壳有变化则暂存包根，由升级收尾当场换入
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

        # 覆盖：白名单外目录整树先删后拷、文件逐个拷，本体走暂存不许直接覆盖
        print("应用更新（保留配置、数据与日志）…")
        for item in new_root.iterdir():
            if item.name in _PRESERVE_NAMES or item.name == _SHELL_EXE:
                continue
            target = root / item.name
            if item.is_dir():
                # 先删后拷：只合并会残留新版已删除的旧代码，遮蔽同名新模块致启动即崩
                shutil.rmtree(target, ignore_errors=True)
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)

        # 换壳：新 exe 与当前不同则暂存包根，升级收尾当场换入
        new_exe = new_root / _SHELL_EXE
        if new_exe.is_file() and not filecmp.cmp(
            new_exe, root / _SHELL_EXE, shallow=False
        ):
            shutil.rmtree(root / _SHELL_PENDING, ignore_errors=True)
            (root / _SHELL_PENDING).mkdir()
            shutil.copy2(new_exe, root / _SHELL_PENDING / _SHELL_EXE)
        return True
    except Exception as e:
        print(f"升级失败：{e}")
        _hold_console()
        return False
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def _check_update(root: Path) -> None:
    """升级检查

    - 网络不通静默跳过
    - GUI 内可手动检查
    """
    local = _local_version(root)
    remote = _remote_version()
    if remote is None or Version(remote) <= Version(local):
        return
    new_msg = f"新版本可用 v{local} -> v{remote}"
    if not _ask_yes_no(f"{new_msg}，立即升级？\n选择否则按当前版本启动。"):
        return
    _open_console()
    print(f"{new_msg}，开始升级…")
    if _apply_update(root, remote):
        # 依赖清单已随包更新：重走安装检查，仅补装变动部分
        _ensure_runtime(root)
        print(f"已升级到 v{remote}")
        _info(f"已升级到 v{remote}")

        # 新壳当场换入并拉起，主程序抢锁后旧壳退场，用户无需关闭再打开
        _apply_shell_update(root, handoff=True)
    elif not _ask_yes_no(
        "升级失败，详情见进度窗口。\n仍以当前版本启动？选否则退出程序。"
    ):
        sys.exit(1)


# ==================== 主流程 ====================


def _apply_shell_update(root: Path, handoff: bool = False) -> None:
    """启动器换壳

    - 启动开头调用只换壳，沿用本次流程
    - 升级收尾带 handoff 则拉起新壳，主程序持锁确认接管后旧壳退场，等不到就回退旧壳直接启动
    """
    pending = root / _SHELL_PENDING
    exe_path = root / _SHELL_EXE
    bak = exe_path.with_name(_SHELL_EXE + _SHELL_BAK_SUFFIX)

    # 每次执行先清理上次换壳的遗留备份
    try:
        bak.unlink(missing_ok=True)
    except OSError:
        pass  # 上次旧壳仍存活或备份被占用，留到下次再清
    new_exe = pending / _SHELL_EXE
    if not new_exe.is_file():
        return
    try:
        exe_path.rename(bak)  # 旧 exe 变身 .old 让位
    except OSError:
        # 改名失败可能是短暂占用，放弃本次更换，保留暂存下次再试
        print("启动器暂被占用，本次沿用旧版继续")
        return
    shutil.move(str(new_exe), str(exe_path))  # 新壳移入规范路径
    shutil.rmtree(pending, ignore_errors=True)

    # 换壳后 exe 路径与文件名未变，Shell 图标缓存认路径不认内容，不刷新则用户端沿用旧图标
    try:
        subprocess.run(
            ["ie4uinit.exe", "-show"],
            creationflags=_CREATE_NO_WINDOW,
            timeout=_ICON_REFRESH_TIMEOUT,
        )
    except Exception:
        pass  # 系统裁剪或刷新超时都不值得拦换壳
    if not handoff:
        return

    subprocess.Popen([str(exe_path)], cwd=str(root), creationflags=_DETACHED_PROCESS)

    # 快交接：新壳数秒内抢锁则用户全程无感
    if _handoff_wait(_SWAP_FAST_TIMEOUT):
        sys.exit(0)

    # 慢路径：新壳多半卡在杀软首扫，安抚窗顶住无反馈时间
    _wait_info(
        "更新完成，正在自动重新启动。\n首次启动需要安全软件扫描，可能要等一会儿…",
        _SWAP_SOOTHE_MS,
    )
    if _handoff_wait(_SWAP_FAST_TIMEOUT + _SWAP_SOOTHE_MS / 1000):
        sys.exit(0)
    print("新壳迟迟未接管（多半是被安全软件首扫拦下），本次由旧壳直接启动")


def _handoff_wait(timeout: float) -> bool:
    """抢锁轮询

    - 锁在新壳主程序手里，抢到即证明新版运行中
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _instance_taken():
            return True
        time.sleep(_HANDOFF_POLL_TICK)
    return False


def _root_dir() -> Path:
    """发布包根目录

    - 启动器 exe 位于包根
    """
    if not getattr(sys, "frozen", False):
        _fail_exit("本文件需经 build.py 编译成 exe 后使用")
    return Path(sys.executable).resolve().parent


def _launch(root: Path) -> None:
    """以无窗口解释器拉起主程序入口脚本

    - 注入源码路径后等价 python -m bot
    - 显式入口便于调试，可直接运行 main.py 复现问题
    """
    env = {
        k: v for k, v in os.environ.items() if k not in ("HTTP_PROXY", "HTTPS_PROXY")
    }  # 剔除安装期注入的代理变量
    env[_AUMID_ANCHOR_VAR] = str(Path(sys.executable))  # 任务栏图标解析指向壳自身
    subprocess.Popen(
        [str(root / "runtime" / "pythonw.exe"), str(root / "main.py")],
        cwd=str(root),
        env=env,
    )


def main() -> None:
    """启动主流程

    - 依次：实例检查、换壳、装环境、检查升级、拉起主程序、回收进度窗口
    """
    if _already_running():
        sys.exit(0)
    root = _root_dir()
    _apply_shell_update(root)
    _apply_system_proxy()
    _ensure_runtime(root)
    _check_update(root)
    _launch(root)
    _close_console()


if __name__ == "__main__":
    main()
