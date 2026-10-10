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
_APP = "FinshinImpact"  # 产物与启动器共用的应用名
_HDR_CONTENT_LENGTH = "Content-Length"
_STAGE = _DIST / _APP
_CACHE = _DIST / "_cache"

# 应用图标唯一来源：随 assets 白名单进发布包，exe 与 GUI 任务栏同源
_ICON = _ROOT / "assets" / "app.ico"

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

# uv 随包下发给启动器装依赖，取用方在 launcher 的 payload 解包
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

# 版本信息网页
_PAGES_PYPROJECT_URL = "https://lym2006.github.io/FinshinImpact/pyproject.toml"

# 发布物探测地址：与 launcher 的下载源同构
_RELEASE_ZIP_URL = "https://github.com/lym2006/FinshinImpact/releases/download/v{ver}/FinshinImpact-v{ver}.zip"
_RELEASE_MIRROR = "https://gh-proxy.com/"

_DOWNLOAD_TIMEOUT = 120.0  # 构建原料下载超时 120 秒（2 分钟）
_CHECK_TIMEOUT = 10.0  # 版本页与发布物探测超时 10 秒
_BYTES_PER_MB = 1024 * 1024  # 1 MB

# 发布 zip 白名单：只装运行必需与用户文档
# devtools、tests、docs、packaging 等开发内容不在名单内，天然排除出发布包
_COPY_DIRS = ("src", "assets")
_COPY_FILES = (
    "pyproject.toml",
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
    _CACHE.mkdir(parents=True, exist_ok=True)
    cached = _CACHE / name
    if cached.exists():
        print(f"命中缓存 {name}")
        return cached
    _download_verified(urls, cached, sha256)
    return cached

def _require_icon() -> bytes:
    """图标原料校验

    - 缺图标即中止构建，不静默放行
    """
    if not _ICON.is_file():
        raise SystemExit(
            f"缺少图标文件 {_ICON}，先生成 app.ico 再构建（见 docs/packaging.md 图标一节）"
        )
    return _ICON.read_bytes()


def _launcher_fingerprint() -> str:
    """启动器产物指纹

    - 源码与图标一并绑定，只换图标也能触发重编译下发新壳
    """
    # 编译动作与产物来源变更绑定
    src = (_ROOT / "packaging" / "launcher.py").read_bytes()
    return hashlib.sha256(src + _require_icon()).hexdigest()


def _build_launcher() -> Path:
    """创建启动器

    - 编译启动器源码为无控制台单目录 exe
    - onedir 不自我解压、默认不压缩，显著降低杀软启发式误报
    - 产物指纹未变时复用已编译产物，exe 哈希不随无关构建漂移，用户端不触发无谓换壳
    """
    out = _DIST / "_launcher" / _APP
    stamp = _DIST / "_launcher" / ".launcher_sha"
    fp = _launcher_fingerprint()
    if (
        (out / f"{_APP}.exe").exists()
        and stamp.exists()
        and stamp.read_text() == fp
    ):
        print("启动器源码与图标未变，复用已编译启动器")
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
            _APP,
            "--icon",
            str(_ICON),
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

# 入口脚本模板：注入源码路径后走引导层，先选实例再拉起主程序
_MAIN_PY = """import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from bootstrap import main

sys.exit(main())
"""


def _write_runtime_seed(launcher_dir: Path) -> None:
    """组装运行原料

    - 启动器 exe 与依赖目录 _internal 放包根，用户双击即见
    """
    runtime = _STAGE / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    shutil.copy2(launcher_dir / f"{_APP}.exe", _STAGE / f"{_APP}.exe")
    shutil.copytree(
        launcher_dir / "_internal",
        _STAGE / "_internal",
        dirs_exist_ok=True,
    )

    shutil.copy2(
        _fetch_to_cache(list(_EMBED_URLS), _EMBED_FILE), runtime / "python-embed.zip"
    )
    payload = _STAGE / "payload"
    payload.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        _fetch_to_cache(list(_UV_URLS), _UV_CACHE_NAME, _UV_SHA256),
        payload / "uv.zip",
    )


def _assemble(launcher_dir: Path) -> Path:
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
    zip_name = _DIST / f"{_APP}-v{version}.zip"
    if zip_name.exists():
        zip_name.unlink()
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in _STAGE.rglob("*"):
            if item.is_file():
                zf.write(item, item.relative_to(_DIST))
    shutil.rmtree(_STAGE)
    return zip_name

def _check_release() -> None:
    """发布前后自检

    - 版本号、远端 tag、本地包指纹、在线版本页、发布物各源可达
    """
    version = _read_version()
    tag_hit = subprocess.run(
        ["git", "ls-remote", "--tags", "origin", f"v{version}"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    zip_path = _DIST / f"{_APP}-v{version}.zip"
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
        ("在线版本页", _remote_version_text()),
    ]
    zip_url = _RELEASE_ZIP_URL.format(ver=version)
    for name, url in (
        ("发布物官方直连", zip_url),
        ("发布物 gh-proxy", _RELEASE_MIRROR + zip_url),
    ):
        checks.append((name, _asset_probe(url, local_size)))
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
        with urllib.request.urlopen(request, timeout=_CHECK_TIMEOUT) as resp:
            remote = int(resp.headers.get(_HDR_CONTENT_LENGTH) or 0)
    except Exception as e:
        return f"不可达（{type(e).__name__}），确认已上传 release"
    if remote == local_size:
        return f"可达，{remote / _BYTES_PER_MB:.1f} MB 与本地包一致"
    return f"可达但大小不符（远端 {remote / _BYTES_PER_MB:.1f} MB）"


def _remote_version_text() -> str:
    """读取版本页版本号文本

    - 读不到不抛错，返回异常类型文本
    """
    try:
        with urllib.request.urlopen(
            _PAGES_PYPROJECT_URL, timeout=_CHECK_TIMEOUT
        ) as resp:
            data = tomllib.loads(resp.read().decode("utf-8"))
        return str(data["project"]["version"])
    except Exception as e:
        # 供自检行降级输出
        return f"读取失败：{type(e).__name__}"

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
        launcher_dir = _DIST / "_launcher" / _APP
        if not (launcher_dir / f"{_APP}.exe").exists():
            print("找不到已有启动器，去掉 --no-launcher 重新编译")
            return
    else:
        launcher_dir = _build_launcher()
    zip_path = _assemble(launcher_dir)
    print(f"完成：{zip_path}")


if __name__ == "__main__":
    main()
