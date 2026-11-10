# src/ui/_guide/_startup.py
"""启动结算

- 插件依赖与资源的安装只发生在启动实例前，装完才起，不带错误启动
- 判定纯实测：启用插件的 pip 包与内核逐项查盘，全齐即静默放行
- 启用集增删不触发结算，缺什么补什么只认实测缺失
- 装失败即禁用相关插件并弹窗告知，降级为不含该插件的启动
- 禁用与卸载分开：结算只装不删，删包只发生在依赖同步里
- 不清包缓存，清理并入依赖管理手动入口
"""

from PySide6.QtWidgets import QMessageBox

from finshin_sdk.domain import ManifestKey
from services.env_setup.assets import install_assets, is_asset_installed
from services.env_setup.deps_install import install_deps
from services.env_setup.deps_startup import disable_failed, target_manifests
from services.env_setup.subprocess_ops import ProgressCallback, emit, is_pin_installed
from services.env_setup.toolchain import dev_mode
from skin.messages import PluginMessage

from .._lifecycle import ensure_app
from ._progress import run_with_progress

# 补装计划条目：(插件名, 缺的 pip 包, 缺的资源)
_Pending = tuple[str, list[str], list[str]]


def _collect_missing(code: str) -> list[_Pending]:
    """逐插件实测并汇总补装计划

    - 空表即环境齐全，启动免结算直接放行
    """
    plan: list[_Pending] = []
    for manifest in target_manifests(code):
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


def _install_missing(
    plan: list[_Pending], on_line: ProgressCallback | None
) -> list[str]:
    """按计划补装缺失依赖与资源

    - 重复安装同一包会快速跳过，被删的内核借同一命令重新下载
    """
    failed: list[str] = []
    for name, missing, assets in plan:
        emit(on_line, PluginMessage.STARTUP_INSTALL.format(name=name))
        failed += install_deps(missing, on_line)
        failed += install_assets(assets, on_line)
    return failed


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
    dropped = disable_failed(code, failed) if failed else []
    if not failed:
        return
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
