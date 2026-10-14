# src/bootstrap/_plugin/_startup.py
"""启动结算

- 插件依赖与资源的安装只发生在启动实例前，装完才起，不带错误启动
- 判定纯实测：启用插件的 pip 包与内核逐项查盘，全齐即静默放行
- 启用集增删不触发结算，缺什么补什么只认实测缺失
- 装失败即禁用相关插件并弹窗告知，降级为不含该插件的启动
- 禁用与卸载分开：结算只装不删，清库只走选窗依赖管理
- 不清包缓存，清理并入依赖管理手动入口
"""

from PySide6.QtWidgets import QMessageBox

from app_icon import ensure_app
from core.domain import ManifestKey, StateKey
from messages import PluginMessage

from ._assets import install_assets, is_asset_installed
from ._env import dev_mode
from ._installer import install_deps
from ._manifest import (
    catalog_digest,
    load_manifests,
    load_state,
    plugins_root,
    save_state,
    top_package_name,
)
from ._progress import run_with_progress
from ._support import ProgressFn, emit, is_pin_installed

# 补装计划条目：(插件名, 缺的 pip 包, 缺的资源)
_Pending = tuple[str, list[str], list[str]]


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


def _collect_missing(code: str) -> list[_Pending]:
    """逐插件实测并汇总补装计划

    - 空表即环境齐全，启动免结算直接放行
    """
    plan: list[_Pending] = []
    for manifest in _target_manifests(code):
        missing = [
            pin for pin in manifest[ManifestKey.DEPS] if not is_pin_installed(pin)
        ]
        assets = [
            asset
            for asset in manifest[ManifestKey.ASSETS]
            if not is_asset_installed(asset)
        ]
        if missing or assets:
            plan.append((manifest[ManifestKey.NAME], missing, assets))
    return plan


def _install_missing(plan: list[_Pending], on_line: ProgressFn | None) -> list[str]:
    """按计划补装缺失依赖与资源

    - 重复安装同一包会快速跳过，被删的内核借同一命令重新下载
    """
    failed: list[str] = []
    for name, missing, assets in plan:
        emit(on_line, PluginMessage.STARTUP_INSTALL.format(name=name))
        failed += install_deps(missing, on_line)
        failed += install_assets(assets, on_line)
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

    - 实测全齐直接返回，不弹任何窗
    - 装失败即禁用相关插件并弹窗告知，不带着错误启动
    - 进度窗任务未完禁关，强退进程等于放弃本次启动
    """
    if dev_mode():
        return
    plan = _collect_missing(code)
    if not plan:
        return
    failed = run_with_progress(
        PluginMessage.PROGRESS_RUNTIME, lambda on_line: _install_missing(plan, on_line)
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
