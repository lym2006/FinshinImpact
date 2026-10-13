# src/bootstrap/_plugin/_startup.py
"""启动结算

- 插件依赖与资源的安装只发生在启动实例前，装完才起，不带错误启动
- 装失败即禁用相关插件并弹窗告知，降级为不含该插件的启动
- 禁用与卸载分开：结算只装不删，清库只走选窗依赖管理
- 判定以环境实测优先，环境被重建过指纹相符也补装
- 全部成功才写指纹留档并清缓存，失败下次启动自动重试
"""

from PySide6.QtWidgets import QMessageBox

from app_icon import ensure_app
from core.domain import ManifestKey, StateKey
from messages import PluginMessage

from ._assets import install_assets
from ._fingerprint import installed_deps_digest, read_fingerprint, save_fingerprint
from ._installer import install_deps
from ._manifest import (
    catalog_digest,
    core_dependencies,
    enabled_assets_union,
    enabled_deps_union,
    load_manifests,
    load_state,
    plugins_root,
    save_state,
    top_package_name,
)
from ._progress import run_with_progress
from ._support import ProgressFn, clean_cache, dev_mode, emit, is_pin_installed


def _target_manifests(code: str) -> list[dict]:
    """取本实例应结算的插件清单

    - 范围为核心插件与本实例启用集
    - core 插件读取侧恒并入，与 utils/plugin/_register 同源口径
    """
    root = plugins_root()
    if root is None:
        return []
    enabled = set(load_state(code).get(StateKey.ENABLED, []))
    return [
        manifest
        for manifest in load_manifests(root)
        if manifest[ManifestKey.CORE] or manifest[ManifestKey.NAME] in enabled
    ]


def _union_digest() -> str:
    """全实例启用依赖与资源并集的指纹

    - runtime 全局共享，指纹按并集而非单实例算，多实例交替启动不反复结算
    """
    pins = [*core_dependencies(), *enabled_deps_union(), *enabled_assets_union()]
    return installed_deps_digest(pins)


def _runtime_pending(code: str) -> bool:
    """判断是否需要启动结算

    - 开发模式启动时跳过自动装卸，只打印手动命令
    - 启用插件的 pip 包逐个实测，环境被同步等操作删过照样查得出
    - 包齐时比对并集指纹，目录变动与启用集变化仍能引发结算
    """
    if dev_mode():
        return False
    for manifest in _target_manifests(code):
        if any(not is_pin_installed(pin) for pin in manifest[ManifestKey.DEPS]):
            return True
    return read_fingerprint() != _union_digest()


def _install_targets(code: str, on_line: ProgressFn | None) -> list[str]:
    """按插件分组补装缺失依赖与资源

    - 重复安装同一包会快速跳过，被删的内核借同一命令重新下载
    """
    failed: list[str] = []
    for manifest in _target_manifests(code):
        missing = [pin for pin in manifest[ManifestKey.DEPS] if not is_pin_installed(pin)]
        assets = list(manifest[ManifestKey.ASSETS])
        if not missing and not assets:
            continue
        emit(on_line, PluginMessage.STARTUP_INSTALL.format(name=manifest[ManifestKey.NAME]))
        failed += install_deps(missing, on_line)
        failed += install_assets(assets, on_line)
    return failed


def _ensure_runtime(code: str, on_line: ProgressFn | None = None) -> list[str]:
    """结算 runtime 依赖并返回失败项

    - 只补装本实例启用插件缺的依赖，不清退任何库
    - 失败不写指纹，下次启动自动重试
    - 全部成功才清包缓存，失败时留缓存供续装命中
    """
    failed = _install_targets(code, on_line)
    if not failed:
        save_fingerprint(_union_digest())
        clean_cache(on_line)
    return failed


def _disable_failed(code: str, failed: list[str]) -> list[str]:
    """把安装失败的启用插件移出启用集并落盘

    - 失败项按顶层包名或资源声明命中哪个插件就禁哪个
    - 命中不了具体插件（整轮异常）时启用集全禁
    - 只改启用集，不动已装库
    """
    root = plugins_root()
    if root is None:
        return []
    enabled = [
        name
        for name in load_state(code).get(StateKey.ENABLED, [])
        if isinstance(name, str)
    ]
    if not enabled:
        return []

    tops = {top_package_name(item) for item in failed}
    dropped: list[str] = []
    for manifest in load_manifests(root):
        name = manifest[ManifestKey.NAME]
        if name not in enabled:
            continue
        deps = {top_package_name(pin) for pin in manifest[ManifestKey.DEPS]}
        assets = set(manifest[ManifestKey.ASSETS])
        if deps & tops or assets & set(failed):
            dropped.append(name)
    if not dropped:
        dropped = list(enabled)

    keep = [name for name in enabled if name not in dropped]
    save_state(code, keep, catalog_digest(load_manifests(root)))
    return dropped


def settle_runtime(code: str) -> None:
    """启动前结算 runtime 依赖，装完才放行启动

    - 装失败即禁用相关插件并弹窗告知，不带着错误启动
    - 进度窗任务未完禁关，强退进程等于放弃本次启动
    """
    if not _runtime_pending(code):
        return
    failed = run_with_progress(
        PluginMessage.PROGRESS_RUNTIME, lambda on_line: _ensure_runtime(code, on_line)
    )
    if not failed:
        return
    dropped = _disable_failed(code, failed)
    ensure_app()
    box = QMessageBox()
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(PluginMessage.SETTLE_TITLE)
    box.setText(
        PluginMessage.STARTUP_FAIL.format(
            plugins="、".join(dropped),
            items="\n".join(map(str, failed)),
        )
    )
    box.exec()
