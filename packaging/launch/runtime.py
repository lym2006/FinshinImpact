# packaging/launch/runtime.py
"""运行环境补齐

- 解压嵌入式 Python、放开 site、部署 uv、清理旧依赖、装依赖
- 已装且清单未变即免装，失败保缓存供续装命中
"""

import hashlib
import shutil
import subprocess
import zipfile
from pathlib import Path

from pack_spec import (
    EMBED_ZIP_NAME,
    RUNTIME_DIR_NAME,
    UV_EXE_NAME,
    UV_PAYLOAD_DIR,
    UV_ZIP_NAME,
    dependencies,
    removed_deps,
    require_setting,
)

from . import console, dialogs

_SETTING_INDEX = "uv-index-urls"  # 换源序列配置键
_SETTING_CACHE = "uv-cache-dir"  # 装包缓存目录配置键


def _list_digest(items: list[str]) -> str:
    """清单指纹

    - 内容变动即指纹变化
    """
    return hashlib.sha256("\n".join(items).encode("utf-8")).hexdigest()


def _installed_ok(runtime: Path, deps: list[str]) -> bool:
    """已装环境且依赖清单未变则免装"""
    stamp = runtime / ".installed"
    if not (runtime / "python.exe").exists() or not stamp.exists():
        return False
    return stamp.read_text() == _list_digest(deps)


def _cleaned_ok(runtime: Path, removed: list[str]) -> bool:
    """清理清单指纹比对"""
    stamp = runtime / ".cleaned"
    return stamp.exists() and stamp.read_text() == _list_digest(removed)


def _extract_embed(runtime: Path) -> None:
    """解压嵌入式 Python 到 runtime 目录"""
    with zipfile.ZipFile(runtime / EMBED_ZIP_NAME) as zf:
        zf.extractall(runtime)


def _enable_site(runtime: Path) -> None:
    """放开嵌入式包的 site-packages

    - 默认被注释锁死，uv 装不进第三方包
    """
    pth = next(iter(runtime.glob("python*._pth")))
    text = pth.read_text()
    if "#import site" in text:
        pth.write_text(text.replace("#import site", "import site"))


def _place_uv(root: Path, runtime: Path) -> Path:
    """复制随包 uv 到 runtime"""
    exe = runtime / UV_EXE_NAME
    if not exe.exists():
        # runtime 在升级保留名单、payload 不在，副本取完即删省磁盘
        with zipfile.ZipFile(root / UV_PAYLOAD_DIR / UV_ZIP_NAME) as zf:
            zf.extract(UV_EXE_NAME, runtime)
    shutil.rmtree(root / UV_PAYLOAD_DIR, ignore_errors=True)
    return exe


def _cleanup_removed(uv: Path, python: Path, removed: list[str], cache: Path) -> None:
    """整批卸载已删依赖的旧残留"""
    # 静默档压掉警告刷屏，真报错仍照常输出
    subprocess.run(
        [
            str(uv),
            "pip",
            "uninstall",
            "--python",
            str(python),
            "--cache-dir",
            str(cache),
            "--quiet",
            *removed,
        ],
        check=True,
    )


def _uv_with_index_retry(
    root: Path, uv: Path, python: Path, deps: list[str], cache: Path
) -> None:
    """换源重试安装依赖"""
    base = [
        str(uv),
        "pip",
        "install",
        "--python",
        str(python),
        "--link-mode",
        "copy",
        "--no-progress",
        "--cache-dir",
        str(cache),
    ]

    # uv 索引按序重试：国内多源轮询，最后官方源兜底
    index_urls = list(require_setting(root, _SETTING_INDEX))
    for i, index in enumerate(index_urls):
        if i:
            print(f"换源重试（第 {i} 次）：{index}")
            print("上方报错无需处理，程序正在自动切换镜像源。\n\n")
        try:
            subprocess.run([*base, "--index-url", index, *deps], check=True)
            return
        except subprocess.CalledProcessError:
            print("\n\n")
            if i == len(index_urls) - 1:
                raise


def ensure_runtime(root: Path) -> None:
    """补齐运行环境

    - 依次：解压嵌入式 Python、放开 site、部署 uv、清理旧依赖、装依赖
    """
    runtime = root / RUNTIME_DIR_NAME

    # 装包期缓存放包内，装完删除，不落用户目录
    cache = runtime / str(require_setting(root, _SETTING_CACHE))
    deps = dependencies(root)
    removed = removed_deps(root)

    # 旧壳升级用 pip 装完时 .cleaned 缺失，新壳须补跑一次清理再按新清单重装
    need_clean = (runtime / "python.exe").exists() and not _cleaned_ok(runtime, removed)
    if _installed_ok(runtime, deps) and not need_clean:
        return
    dialogs.info("首次运行需要安装运行环境，期间保持网络畅通，可能需要几分钟。")
    console.open_console()
    try:
        print("[1/4] 解压嵌入式 Python…")
        if not (runtime / "python.exe").exists():
            _extract_embed(runtime)
        print("[2/4] 放开 site-packages…")
        _enable_site(runtime)
        print("[3/4] 准备安装器 uv…")
        uv = _place_uv(root, runtime)
        print("[4/4] 清理旧依赖并安装（下方为 uv 实时输出）…")
        _cleanup_removed(uv, runtime / "python.exe", removed, cache)
        _uv_with_index_retry(root, uv, runtime / "python.exe", deps, cache)
        print("环境安装完成，即将启动主程序")
    except subprocess.CalledProcessError:
        # 失败不删缓存，续装直接命中省下载
        dialogs.fail_exit(
            "依赖安装失败，请查看进度窗口末尾输出\n恢复网络后重新双击即可续装"
        )
    except FileNotFoundError as e:
        dialogs.fail_exit(f"安装文件缺失：{e}\n发布包可能损坏，请重新下载")
    except zipfile.BadZipFile:
        dialogs.fail_exit(
            "内嵌运行环境包损坏（发布物不完整）\n请到 Releases 页重新下载最新发布包"
        )

    # 装完即删：缓存在用户目录会留近 400MB 运行期无用的副本，改放包内用完清掉
    shutil.rmtree(cache, ignore_errors=True)
    (runtime / ".installed").write_text(_list_digest(deps))
    (runtime / ".cleaned").write_text(_list_digest(removed))
