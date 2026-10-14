# packaging/build.py
"""发布构建脚本

- 编译启动器并组装 zip 发布物
- 原料下载在 pack_fetch，发布自检在 pack_release
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pack_fetch
import pack_release
from pack_spec import (
    APP_NAME,
    DIST,
    EMBED_ZIP_NAME,
    EXE_NAME,
    ROOT,
    STAGE,
    UV_PAYLOAD_DIR,
    UV_ZIP_NAME,
    local_version,
)

# 应用图标唯一来源：随 assets 白名单进发布包，exe 与 GUI 任务栏同源
_ICON = ROOT / "assets" / "app.ico"

# 发布 zip 白名单：只装运行必需与用户文档，devtools/tests/docs/packaging 不在名单天然排除
_COPY_DIRS = ("src", "assets")
_COPY_FILES = (
    "pyproject.toml",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
)

# 入口脚本模板：注入源码路径后走引导层，先选实例再拉起主程序
_MAIN_PY = """import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from bootstrap import main

sys.exit(main())
"""


def _require_icon() -> bytes:
    """图标原料校验

    - 缺图标即中止构建，不静默放行
    """
    if not _ICON.is_file():
        raise SystemExit(
            f"缺少图标文件 {_ICON}，先生成 app.ico 再构建（见 docs/packaging.md 图标一节）"
        )
    return _ICON.read_bytes()


def _launcher_sources() -> list[Path]:
    """列出编译进启动器的全部源文件"""
    pkg = ROOT / "packaging"
    paths = [pkg / "launcher.py", pkg / "pack_spec.py"]
    paths.extend(sorted((pkg / "launch").glob("*.py")))
    return paths


def _launcher_fingerprint() -> str:
    """启动器产物指纹

    - 源码与图标一并计入，只换图标也会重编译
    - 入口、共享规格与 launch 域全部计入，域代码变更同样重编译
    """
    # 编译动作与产物来源变更绑定
    blob = b"".join(
        f"=={p.name}==\n".encode() + p.read_bytes() for p in _launcher_sources()
    )
    return hashlib.sha256(blob + _require_icon()).hexdigest()


def _build_launcher() -> Path:
    """创建启动器

    - 编译启动器源码为无控制台单目录 exe
    - onedir 不解压不压缩，降低杀毒软件误报
    - 产物指纹未变时复用已编译产物，避免用户端重复下载
    """
    out = DIST / "_launcher" / APP_NAME
    stamp = DIST / "_launcher" / ".launcher_sha"
    fp = _launcher_fingerprint()
    if (out / EXE_NAME).exists() and stamp.exists() and stamp.read_text() == fp:
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
            APP_NAME,
            "--icon",
            str(_ICON),
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
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(fp)
    return out


def _write_runtime_seed(launcher_dir: Path) -> None:
    """组装运行原料

    - 启动器 exe 与依赖目录 _internal 放包根，用户双击即见
    """
    runtime = STAGE / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    shutil.copy2(launcher_dir / EXE_NAME, STAGE / EXE_NAME)
    shutil.copytree(
        launcher_dir / "_internal",
        STAGE / "_internal",
        dirs_exist_ok=True,
    )

    shutil.copy2(pack_fetch.fetch_embed(), runtime / EMBED_ZIP_NAME)
    payload = STAGE / UV_PAYLOAD_DIR
    payload.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pack_fetch.fetch_uv(), payload / UV_ZIP_NAME)


def _assemble(launcher_dir: Path) -> Path:
    """组装发布目录并压缩为 zip"""
    version = local_version(ROOT)
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    for name in _COPY_DIRS:
        src = ROOT / name
        if src.exists():
            shutil.copytree(
                src,
                STAGE / name,
                ignore=shutil.ignore_patterns(
                    "__pycache__", ".pytest_cache", "*.egg-info"
                ),
            )
    for name in _COPY_FILES:
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, STAGE / name)

    (STAGE / "main.py").write_text(_MAIN_PY, encoding="utf-8")
    _write_runtime_seed(launcher_dir)
    zip_name = DIST / f"{APP_NAME}-v{version}.zip"
    if zip_name.exists():
        zip_name.unlink()
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in STAGE.rglob("*"):
            if item.is_file():
                zf.write(item, item.relative_to(DIST))
    shutil.rmtree(STAGE)
    return zip_name


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
        pack_release.check_release()
        return

    version = local_version(ROOT)
    if version.endswith("-dev") and not args.force:
        print(f"当前版本号 {version} 含 -dev 后缀，拒绝构建")
        print("确认要构建请加 --force；发布前请先定稿正式版本号并打 tag")
        return

    if args.no_launcher:
        launcher_dir = DIST / "_launcher" / APP_NAME
        if not (launcher_dir / EXE_NAME).exists():
            print("找不到已有启动器，去掉 --no-launcher 重新编译")
            return
    else:
        launcher_dir = _build_launcher()
    zip_path = _assemble(launcher_dir)
    print(f"完成：{zip_path}")


if __name__ == "__main__":
    main()
