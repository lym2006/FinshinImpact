# packaging/build.py
"""发布构建脚本

- 编译启动器并组装 zip 发布物
- 自检发布状态（远端 tag 与在线版本页）
"""

import argparse
import shutil
import subprocess
import sys
import tomllib
import urllib.request
import zipfile
from pathlib import Path

# 仓库根与产物目录
ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
STAGE = DIST / "TelegramBot"

# 嵌入式发行版官方直链（构建时另有 npmmirror 兜底）与 pip 引导脚本
EMBED_VERSION = "3.11.9"
EMBED_URL = (
    f"https://www.python.org/ftp/python/{EMBED_VERSION}"
    f"/python-{EMBED_VERSION}-embed-amd64.zip"
)
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"

# 发布 zip 的白名单：只装运行必需与用户文档，开发配置与残留全部排除
COPY_DIRS = ("src", "assets")
COPY_FILES = (
    "pyproject.toml",
    "config.example.toml",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
)


def _read_version() -> str:
    """本地 pyproject.toml 的版本号"""
    with open(ROOT / "pyproject.toml", "rb") as f:
        return str(tomllib.load(f)["project"]["version"])


def _download(url: str, target: Path) -> None:
    """下载文件到指定路径"""
    print(f"下载 {url}")
    with urllib.request.urlopen(url, timeout=120.0) as resp, open(target, "wb") as f:
        shutil.copyfileobj(resp, f)


def _download_verified(urls: list[str], target: Path) -> None:
    """多源下载并逐条目校验 zip

    网络截断的半截文件也能正常落盘，出厂前必须验证完整。
    """
    last_error: Exception | None = None
    for url in urls:
        try:
            _download(url, target)
            with zipfile.ZipFile(target) as zf:
                if zf.testzip() is None:
                    return
            raise zipfile.BadZipFile("zip 条目校验失败")
        except Exception as e:
            last_error = e
            print(f"该源失败（{e}），尝试下一个")
    raise RuntimeError(f"全部下载源均损坏，中止构建：{last_error}")


# ==================== 启动器编译 ====================


def build_launcher() -> Path:
    """创建启动器

    编译启动器源码为无控制台单目录 exe。
    onedir 不自我解压、默认不压缩，显著降低杀软启发式误报。
    """
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
            str(DIST / "_launcher"),
            "--workpath",
            str(DIST / "build"),
            "--specpath",
            str(DIST),
            str(ROOT / "packaging" / "launcher.py"),
        ],
        check=True,
    )
    return DIST / "_launcher" / "TelegramBot"


# ==================== 发布物组装 ====================


# 入口脚本模板：注入源码路径后等价 python -m bot
MAIN_PY = """import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from bot.__main__ import Main

sys.exit(Main().main())
"""


def _write_runtime_seed(launcher_dir: Path) -> None:
    """组装运行原料

    组装嵌入式 Python 与 pip 引导脚本进 runtime。
    启动器 exe 与其依赖目录 _internal 放包根，用户双击即见。
    """
    runtime = STAGE / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    shutil.copy2(launcher_dir / "TelegramBot.exe", STAGE / "TelegramBot.exe")
    shutil.copytree(
        launcher_dir / "_internal",
        STAGE / "_internal",
        dirs_exist_ok=True,
    )

    # 四源实测可达：官方 → npmmirror → 华为云 → 淘宝
    embed_candidates = [
        EMBED_URL,
        "https://registry.npmmirror.com/-/binary/python/"
        + f"{EMBED_VERSION}/python-{EMBED_VERSION}-embed-amd64.zip",
        "https://mirrors.huaweicloud.com/python/"
        + f"{EMBED_VERSION}/python-{EMBED_VERSION}-embed-amd64.zip",
        "https://npmmirror.com/mirrors/python/"
        + f"{EMBED_VERSION}/python-{EMBED_VERSION}-embed-amd64.zip",
    ]
    _download_verified(embed_candidates, runtime / "python-embed.zip")
    _download(GET_PIP_URL, runtime / "get-pip.py")


def assemble(launcher_dir: Path) -> Path:
    """组装发布目录并压缩为 zip"""
    version = _read_version()
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    for name in COPY_DIRS:
        src = ROOT / name
        if src.exists():
            shutil.copytree(
                src,
                STAGE / name,
                ignore=shutil.ignore_patterns(
                    "__pycache__", ".pytest_cache", "*.egg-info"
                ),
            )
    for name in COPY_FILES:
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, STAGE / name)

    (STAGE / "main.py").write_text(MAIN_PY, encoding="utf-8")
    _write_runtime_seed(launcher_dir)
    zip_name = DIST / f"TelegramBot-v{version}.zip"
    if zip_name.exists():
        zip_name.unlink()
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in STAGE.rglob("*"):
            if item.is_file():
                zf.write(item, item.relative_to(DIST))
    shutil.rmtree(STAGE)
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
        ("本地 zip", (DIST / f"TelegramBot-v{version}.zip").exists()),
        (
            "在线版本页一致",
            _remote_version_text(),
        ),
    ]
    for name, detail in checks:
        print(f"[自检] {name}: {detail}")


def _remote_version_text() -> str:
    """读取版本页版本号文本（读不到显示原因，不抛异常）"""
    try:
        with urllib.request.urlopen(
            "https://lym2006.github.io/TelegramBot/pyproject.toml", timeout=10.0
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
        launcher_dir = DIST / "_launcher" / "TelegramBot"
        if not (launcher_dir / "TelegramBot.exe").exists():
            print("找不到已有启动器，去掉 --no-launcher 重新编译")
            return
    else:
        launcher_dir = build_launcher()
    zip_path = assemble(launcher_dir)
    print(f"完成：{zip_path}")


if __name__ == "__main__":
    main()
