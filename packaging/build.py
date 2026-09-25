# packaging/build.py
"""发布构建脚本

- 编译启动器并组装 zip 发布物
- 自检发布状态（远端 tag 与在线版本页）
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
import tomllib
import urllib.request
import zipfile
from pathlib import Path

# 仓库根与产物目录（_cache 存放重复构建可复用的原料）
_ROOT = Path(__file__).resolve().parent.parent
_DIST = _ROOT / "dist"
_STAGE = _DIST / "TelegramBot"
_CACHE = _DIST / "_cache"

# 构建原料下载源：镜像优先、官方兜底；版本页是在线版本比对唯一真相
_EMBED_VERSION = "3.11.9"
_EMBED_FILE = f"python-{_EMBED_VERSION}-embed-amd64.zip"
_EMBED_URL_SUFFIX = f"python/{_EMBED_VERSION}/{_EMBED_FILE}"
_EMBED_URLS = (
    f"https://registry.npmmirror.com/-/binary/{_EMBED_URL_SUFFIX}",
    f"https://mirrors.huaweicloud.com/{_EMBED_URL_SUFFIX}",
    f"https://npmmirror.com/mirrors/{_EMBED_URL_SUFFIX}",
    f"https://www.python.org/ftp/{_EMBED_URL_SUFFIX}",
)
_GET_PIP_URLS = (
    "https://mirrors.aliyun.com/pypi/get-pip.py",
    "https://bootstrap.pypa.io/get-pip.py",
)
_PAGES_PYPROJECT_URL = "https://lym2006.github.io/TelegramBot/pyproject.toml"

_DOWNLOAD_TIMEOUT = 120.0  # 构建原料下载超时 120 秒（2 分钟）
_CHECK_TIMEOUT = 10.0  # 版本页自检超时 10 秒
_SHEBANG_PROBE = 32  # 脚本原料头部探测长度 32 字节

# 发布 zip 的白名单：只装运行必需与用户文档，开发配置与残留全部排除
_COPY_DIRS = ("src", "assets")
_COPY_FILES = (
    "pyproject.toml",
    "config.example.toml",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
)


def _read_version() -> str:
    """本地 pyproject.toml 的版本号"""
    with open(_ROOT / "pyproject.toml", "rb") as f:
        return str(tomllib.load(f)["project"]["version"])


def _download(url: str, target: Path) -> None:
    """下载文件到指定路径

    中断的半截文件不许以正式名存在，故原子落盘、失败清残留。
    """
    print(f"下载 {url}")
    part = target.with_name(target.name + ".part")  # 半成品用临时名
    try:
        with (
            urllib.request.urlopen(url, timeout=_DOWNLOAD_TIMEOUT) as resp,
            open(part, "wb") as f,
        ):
            shutil.copyfileobj(resp, f)
        part.replace(target)
    except Exception:
        part.unlink(missing_ok=True)
        raise


def _download_verified(urls: list[str], target: Path) -> None:
    """构建原料多源下载

    半截文件也能正常落盘，出厂前必须验完整性：zip 验条目、
    脚本验头，任一校验不过即视为该源失败，换下一源。
    """
    last_error: Exception | None = None
    for url in urls:
        try:
            _download(url, target)
            if target.suffix == ".zip":
                with zipfile.ZipFile(target) as zf:
                    if zf.testzip() is not None:
                        raise zipfile.BadZipFile("zip 条目校验失败")
            else:
                with open(target, "rb") as f:
                    head = f.read(_SHEBANG_PROBE)
                if not head.startswith(b"#"):
                    raise ValueError("下载内容不是脚本")  # 镜像返回错误页
            return
        except Exception as e:
            last_error = e
            print(f"该源失败（{e}），尝试下一个")
    target.unlink(missing_ok=True)
    raise RuntimeError(f"全部下载源均失败，中止构建：{last_error}")


def _fetch_to_cache(urls: list[str], name: str) -> Path:
    """构建原料取用缓存

    原料跨构建复用，清 dist 目录即清缓存。
    """
    _CACHE.mkdir(parents=True, exist_ok=True)
    cached = _CACHE / name
    if cached.exists():
        print(f"命中缓存 {name}")
        return cached
    _download_verified(urls, cached)
    return cached


# ==================== 启动器编译 ====================


def _launcher_fingerprint() -> str:
    """启动器源码指纹

    编译动作与源码变更绑定，免受 PyInstaller 输出自带时间戳干扰。
    """
    src = (_ROOT / "packaging" / "launcher.py").read_bytes()
    return hashlib.sha256(src).hexdigest()


def build_launcher() -> Path:
    """创建启动器

    编译启动器源码为无控制台单目录 exe；onedir 不自我解压、
    默认不压缩，显著降低杀软启发式误报。源码指纹未变时复用
    已编译产物，exe 哈希不随无关构建漂移，用户端不触发无谓换壳。
    """
    out = _DIST / "_launcher" / "TelegramBot"
    stamp = _DIST / "_launcher" / ".launcher_sha"
    fp = _launcher_fingerprint()
    if (
        (out / "TelegramBot.exe").exists()
        and stamp.exists()
        and stamp.read_text() == fp
    ):
        print("launcher.py 未变，复用已编译启动器")
        return out
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onedir",
            "--noconsole",
            "--name",
            "TelegramBot",
            "--distpath",
            str(_DIST / "_launcher"),
            "--workpath",
            str(_DIST / "build"),
            "--specpath",
            str(_DIST),
            str(_ROOT / "packaging" / "launcher.py"),
        ],
        check=True,
    )
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(fp)
    return out


# ==================== 发布物组装 ====================


# 入口脚本模板：注入源码路径后等价 python -m bot
_MAIN_PY = """import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from bot.__main__ import Main

sys.exit(Main().main())
"""


def _write_runtime_seed(launcher_dir: Path) -> None:
    """组装运行原料

    启动器 exe 与其依赖目录 _internal 放包根，用户双击即见。
    """
    runtime = _STAGE / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    shutil.copy2(launcher_dir / "TelegramBot.exe", _STAGE / "TelegramBot.exe")
    shutil.copytree(
        launcher_dir / "_internal",
        _STAGE / "_internal",
        dirs_exist_ok=True,
    )

    shutil.copy2(
        _fetch_to_cache(list(_EMBED_URLS), _EMBED_FILE), runtime / "python-embed.zip"
    )
    shutil.copy2(
        _fetch_to_cache(list(_GET_PIP_URLS), "get-pip.py"),
        runtime / "get-pip.py",
    )


def assemble(launcher_dir: Path) -> Path:
    """组装发布目录并压缩为 zip"""
    version = _read_version()
    if _STAGE.exists():
        shutil.rmtree(_STAGE)
    _STAGE.mkdir(parents=True)

    for name in _COPY_DIRS:
        src = _ROOT / name
        if src.exists():
            shutil.copytree(
                src,
                _STAGE / name,
                ignore=shutil.ignore_patterns(
                    "__pycache__", ".pytest_cache", "*.egg-info"
                ),
            )
    for name in _COPY_FILES:
        src = _ROOT / name
        if src.exists():
            shutil.copy2(src, _STAGE / name)

    (_STAGE / "main.py").write_text(_MAIN_PY, encoding="utf-8")
    _write_runtime_seed(launcher_dir)
    zip_name = _DIST / f"TelegramBot-v{version}.zip"
    if zip_name.exists():
        zip_name.unlink()
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in _STAGE.rglob("*"):
            if item.is_file():
                zf.write(item, item.relative_to(_DIST))
    shutil.rmtree(_STAGE)
    return zip_name


# ==================== 本地自检 ====================


def _check_release() -> None:
    """发布前四项核对：版本号、远端 tag、发布物、在线版本页"""
    version = _read_version()
    tag_hit = subprocess.run(
        ["git", "ls-remote", "--tags", "origin", f"v{version}"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    checks = [
        (
            "本地版本号",
            f"v{version}" if not version.endswith("-dev") else "开发号，先正式化",
        ),
        ("git tag 远端", "已推送" if tag_hit else "缺失，先 push tag"),
        ("本地 zip", (_DIST / f"TelegramBot-v{version}.zip").exists()),
        (
            "在线版本页一致",
            _remote_version_text(),
        ),
    ]
    for name, detail in checks:
        print(f"[自检] {name}: {detail}")


def _remote_version_text() -> str:
    """读取版本页版本号文本

    读不到显示异常类型而不抛错，供自检行降级输出。
    """
    try:
        with urllib.request.urlopen(
            _PAGES_PYPROJECT_URL, timeout=_CHECK_TIMEOUT
        ) as resp:
            data = tomllib.loads(resp.read().decode("utf-8"))
        return str(data["project"]["version"])
    except Exception as e:
        return f"读取失败：{type(e).__name__}"


# ==================== 入口 ====================


def main() -> None:
    """解析参数并执行构建流程"""
    parser = argparse.ArgumentParser(description="发布构建")
    parser.add_argument("--check", action="store_true", help="发布前自检")
    parser.add_argument(
        "--no-launcher", action="store_true", help="跳过编译复用现有启动器"
    )
    parser.add_argument("--force", action="store_true", help="允许开发号版本号构建")
    args = parser.parse_args()

    if args.check:
        _check_release()
        return

    version = _read_version()
    if version.endswith("-dev") and not args.force:
        print(f"当前版本号 {version} 含 -dev 后缀，拒绝构建")
        print("确认要构建请加 --force；发布前请先定稿正式版本号并打 tag")
        return

    if args.no_launcher:
        launcher_dir = _DIST / "_launcher" / "TelegramBot"
        if not (launcher_dir / "TelegramBot.exe").exists():
            print("找不到已有启动器，去掉 --no-launcher 重新编译")
            return
    else:
        launcher_dir = build_launcher()
    zip_path = assemble(launcher_dir)
    print(f"完成：{zip_path}")


if __name__ == "__main__":
    main()
