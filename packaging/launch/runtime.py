"""运行环境补齐

- 解压嵌入式 Python、放开 site、部署 uv、装依赖
- 随包接口件与核心依赖一条命令装齐
- 已装且清单未变即免装，失败保缓存供续装命中
- 随包件同版本照装，本机更高的版本不许被压回去
"""

import shutil
import subprocess
import zipfile
from pathlib import Path

from pack_spec import (
    PackLayout,
    dependencies,
    lines_digest,
    require_setting,
)
from packaging.version import InvalidVersion, Version
from unpack import unpack_all, unpack_entry

from . import console, dialogs

# 换源与缓存的配置键，随包接口件的形态
_SETTING_INDEX = "uv-index-urls"
_SETTING_CACHE = "uv-cache-dir"
_WHEEL_GLOB = "*.whl"

# 运行环境里已装件的落点与命名形态
_SITE_PACKAGES = Path("Lib") / "site-packages"
_DIST_INFO_GLOB = "*.dist-info"
_DIST_INFO_SUFFIX = ".dist-info"


def _seed_wheels(root: Path) -> list[Path]:
    """随包接口件的 wheel，按文件名升序

    - 构建时打进包根 `_sdk`，升级整目录替换
    """
    return sorted((root / PackLayout.SDK_WHEEL_DIR).glob(_WHEEL_GLOB))


def _name_and_version(stem: str) -> tuple[str, str]:
    """文件名头两段读成发行件名与版本，下划线归回连字符"""
    parts = stem.split("-")
    if len(parts) < 2:
        return "", ""
    return parts[0].replace("_", "-"), parts[1]


def _installed_versions(runtime: Path) -> dict[str, str]:
    """运行环境里已装的发行件名与版本，按 dist-info 目录名读"""
    found: dict[str, str] = {}
    for info in (runtime / _SITE_PACKAGES).glob(_DIST_INFO_GLOB):
        name, version = _name_and_version(info.name[: -len(_DIST_INFO_SUFFIX)])
        if name:
            found[name] = version
    return found


def _already_enough(wheel: Path, installed: dict[str, str]) -> bool:
    """随包件要的那版本机已有更高才算够，读不懂版本即算不足

    - 同版本照装：重打不抬版本号的件只靠这一步换掉
    """
    name, wanted = _name_and_version(wheel.stem)
    have = installed.get(name, "")
    if not have:
        return False
    try:
        return Version(have) > Version(wanted)
    except InvalidVersion:
        return False


def _install_plan(root: Path) -> tuple[list[str], list[str]]:
    """交给 uv 的装单与记进免装指纹的清单

    - 随包接口件按路径喂 uv，本机已装高于那版才不进装单
    - 指纹只记核心依赖，随包件装成功就被删
    """
    core = dependencies(root)
    installed = _installed_versions(root / PackLayout.RUNTIME_DIR)
    pending = _seed_wheels(root)
    wanted = [wheel for wheel in pending if not _already_enough(wheel, installed)]

    return [*core, *(str(wheel) for wheel in wanted)], core


def _drop_seeds(root: Path) -> None:
    """装成功后删掉随包接口件那一份

    - 整目录删，装过之后没人再读它
    - 失败路径不走到这里，留下的件供下次续装命中
    """
    shutil.rmtree(root / PackLayout.SDK_WHEEL_DIR, ignore_errors=True)


def _list_digest(items: list[str]) -> str:
    """清单指纹

    - 内容变动即指纹变化
    """
    return lines_digest(items)


def _installed_ok(runtime: Path, deps: list[str]) -> bool:
    """已装环境且依赖清单未变则免装"""
    stamp = runtime / PackLayout.INSTALL_STAMP
    if not (runtime / PackLayout.PYTHON_EXE).exists() or not stamp.exists():
        return False
    return stamp.read_text() == _list_digest(deps)


def _extract_embed(runtime: Path) -> None:
    """解压嵌入式 Python 到 runtime 目录"""
    unpack_all(runtime / PackLayout.EMBED_ZIP, runtime)


def _enable_site(runtime: Path) -> None:
    """放开嵌入式包的 site-packages"""
    pth = next(iter(runtime.glob(PackLayout.PYTHON_PTH_GLOB)))
    text = pth.read_text()

    # 默认那行被注释锁死，uv 装不进第三方包
    if "#import site" in text:
        pth.write_text(text.replace("#import site", "import site"))


def _place_uv(root: Path, runtime: Path) -> Path:
    """复制随包 uv 到 runtime"""
    exe = runtime / PackLayout.UV_EXE
    if not exe.exists():
        # runtime 在升级保留名单、payload 不在，副本取完即删省磁盘
        unpack_entry(
            root / PackLayout.PAYLOAD_DIR / PackLayout.UV_ZIP,
            PackLayout.UV_EXE,
            runtime,
        )
    shutil.rmtree(root / PackLayout.PAYLOAD_DIR, ignore_errors=True)
    return exe


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

    - 依次：解压嵌入式 Python、放开 site、部署 uv、装依赖
    - 只追加安装，删掉的库由引导层同步环境收口
    - 装包缓存不在此清，留到引导层同步落定后收口
    - 随包接口件装成功即从包根删掉，装失败留着下次续装命中
    """
    runtime = root / PackLayout.RUNTIME_DIR

    # 装包期缓存放包内，不落用户目录
    cache = runtime / str(require_setting(root, _SETTING_CACHE))
    deps, stamped = _install_plan(root)

    # 随包件在场即说明有一趟待装，指纹相同也要跑
    if not _seed_wheels(root) and _installed_ok(runtime, stamped):
        return
    fresh = not (runtime / PackLayout.PYTHON_EXE).exists()
    dialogs.info("首次运行需要安装运行环境" if fresh else "升级后补装变动依赖")
    console.open_console()
    try:
        print("[1/3] 解压嵌入式 Python…")
        if not (runtime / PackLayout.PYTHON_EXE).exists():
            _extract_embed(runtime)
        print("[2/3] 放开 site-packages…")
        _enable_site(runtime)
        print("[3/3] 准备安装器 uv 并装依赖（下方为 uv 实时输出）…")
        uv = _place_uv(root, runtime)
        _uv_with_index_retry(root, uv, runtime / PackLayout.PYTHON_EXE, deps, cache)
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
            "内嵌运行环境包损坏（发布包不完整）\n请到 Releases 页重新下载最新发布包"
        )

    (runtime / PackLayout.INSTALL_STAMP).write_text(_list_digest(stamped))
    _drop_seeds(root)
