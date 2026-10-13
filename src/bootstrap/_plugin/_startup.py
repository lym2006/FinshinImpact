# src/bootstrap/_plugin/_startup.py
"""启动结算

- 插件依赖与资源的装卸只发生在启动实例前，按插件分组补缺
- 所有实例都不再启用的库才卸载，仍被任一实例启用的保留
- 指纹与全实例启用并集相符即免结算，全部装完才写指纹
"""

from PySide6.QtWidgets import QMessageBox

from app_icon import ensure_app
from core.domain import ManifestKey, StateKey
from messages import PluginMessage

from ._assets import install_assets, uninstall_assets
from ._fingerprint import installed_deps_digest, read_fingerprint, save_fingerprint
from ._installer import install_deps, uninstall_deps
from ._manifest import (
    core_dependencies,
    enabled_assets_union,
    enabled_deps_union,
    enabled_names_union,
    load_manifests,
    load_state,
    plugins_root,
    top_package_name,
)
from ._progress import run_with_progress
from ._support import ProgressFn, dev_mode, emit, is_pin_installed


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


def _runtime_pending() -> bool:
    """判断是否需要启动结算

    - 开发模式启动时跳过自动装卸，只打印手动命令
    """
    if dev_mode() or read_fingerprint() == _union_digest():
        return False
    return True


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


def _purge_orphans(on_line: ProgressFn | None) -> list[str]:
    """卸载所有实例都不再启用的库

    - 保留清单并入 core 与全实例启用并集，仍被引用的顶层包不卸
    - 资源模块未安装即跳过，playwright 缺失时 uninstall 命令会报错
    - 顺序先资源后包，内核卸载依赖 playwright 模块仍在
    """
    root = plugins_root()
    if root is None:
        return []
    holders = enabled_names_union()
    keep_tops = {
        top_package_name(pin)
        for pin in [*core_dependencies(), *enabled_deps_union()]
    }
    keep_assets = set(enabled_assets_union())

    tops: list[str] = []
    assets: list[str] = []
    for manifest in load_manifests(root):
        if manifest[ManifestKey.NAME] in holders:
            continue
        for pin in manifest[ManifestKey.DEPS]:
            top = top_package_name(pin)
            if (
                top not in keep_tops
                and top not in tops
                and is_pin_installed(pin)
            ):
                tops.append(top)
        for asset in manifest[ManifestKey.ASSETS]:
            if asset not in keep_assets and is_pin_installed(asset):
                assets.append(asset)

    if not tops and not assets:
        return []
    emit(on_line, PluginMessage.STARTUP_PURGE)
    return uninstall_assets(assets, on_line) + uninstall_deps(tops, on_line)


def _ensure_runtime(code: str, on_line: ProgressFn | None = None) -> list[str]:
    """结算 runtime 依赖并返回失败项

    - 先装本实例缺失的依赖，再卸所有实例都不用的库
    - 失败不写指纹，下次启动自动重试
    """
    failed = _install_targets(code, on_line)
    failed += _purge_orphans(on_line)
    if not failed:
        save_fingerprint(_union_digest())
    return failed


def settle_runtime(code: str) -> None:
    """启动前结算 runtime 依赖

    - 失败弹窗提示但不阻断启动，相关命令可能不可用
    - 强关进度窗后任务转后台，本轮按失败计不写指纹
    """
    if not _runtime_pending():
        return
    failed = run_with_progress(
        PluginMessage.PROGRESS_RUNTIME, lambda on_line: _ensure_runtime(code, on_line)
    )
    if not failed:
        return
    ensure_app()
    box = QMessageBox()
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(PluginMessage.SETTLE_TITLE)
    box.setText(PluginMessage.STARTUP_FAIL.format(items="\n".join(map(str, failed))))
    box.exec()
