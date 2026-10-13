# src/bootstrap/_slot.py
"""启动资格判定

- 引导锁内完成实例身份选择与实例锁抢占
- 非正常启动结果分别提示并给出退出码
- 抢到实例锁才导入主程序，路径常量在导入期随身份码确定
"""

from enum import IntEnum

from instance_lock import (
    acquire_bootstrap_lock,
    acquire_instance_lock,
    release_bootstrap_lock,
)
from profile_env import get_profile, set_profile


class _SlotResult(IntEnum):
    """启动资格结果

    - 值只作分支标识，不参与比较
    """

    RUN = 0
    CANCEL = 1
    CONFLICT = 2
    PICKER_BUSY = 3


def _acquire_slot() -> _SlotResult:
    """取得本实例的启动资格

    - 引导锁内先选身份再抢实例锁，两锁交接无间隙
    - 引导锁被占说明已有选择窗打开，本进程直接退出
    - 选窗关闭即释放引导锁，运行期间双击启动器仍可再开选择窗
    """
    profile = get_profile()
    if profile:
        # 预设身份：不弹选窗，无需引导锁，结算与抢实例锁前完成
        from ._plugin import settle_runtime

        settle_runtime(profile)
        return _SlotResult.RUN if acquire_instance_lock() else _SlotResult.CONFLICT

    if not acquire_bootstrap_lock():
        return _SlotResult.PICKER_BUSY

    try:
        # 延迟导入：选窗依赖 Qt，且必须早于 bot/utils
        from ._picker import pick_profile

        code = pick_profile()
        if not code:
            return _SlotResult.CANCEL

        # 身份码落环境变量后路径常量才按实例冻结，须早于任何 utils 导入
        set_profile(code)

        # 插件目录与实例状态指纹不符即弹面板，取消视为放弃本次启动
        from ._plugin import MODE_AUTO, open_panel, panel_needed, settle_runtime

        if panel_needed(code) and not open_panel(code, MODE_AUTO):
            return _SlotResult.CANCEL

        # 启用集变动只在此刻结算，缺库补装、无主库删除，装完才起
        settle_runtime(code)

        if not acquire_instance_lock():
            return _SlotResult.CONFLICT
        return _SlotResult.RUN
    finally:
        release_bootstrap_lock()


def _popup(title_text: str, body: str, *, icon_warning: bool = True) -> None:
    """提示弹窗

    - 延迟导入，只在真正弹窗时加载选窗模块与图标
    """
    from PySide6.QtWidgets import QMessageBox

    from app_icon import ensure_app

    from ._qss import build_bootstrap_qss

    ensure_app()
    box = QMessageBox()
    box.setStyleSheet(build_bootstrap_qss())
    box.setIcon(
        QMessageBox.Icon.Warning if icon_warning else QMessageBox.Icon.Information
    )
    box.setWindowTitle(title_text)
    box.setText(body)
    box.exec()


def _handle(result: _SlotResult) -> int | None:
    """非 RUNNING 结果的处理

    - 返回退出码，RUNNING 返回 None 交调用方继续启动
    - 选窗取消时静默退出
    - 引导锁被占与实例冲突各弹对应提示
    """
    if result is _SlotResult.RUN:
        return None

    if result is _SlotResult.CANCEL:
        return 0

    if result is _SlotResult.PICKER_BUSY:
        from messages import PickerMessage

        _popup(PickerMessage.TITLE, PickerMessage.BUSY, icon_warning=False)
        return 0

    from gui._theme import GLOBAL, WINDOW

    _popup(WINDOW.title, GLOBAL.already_running)
    return 0


def main() -> int:
    """引导入口

    - 完成资格判定后，持锁进程才导入主程序
    - 须先写入身份码环境变量，再导入路径常量
    """
    code = _handle(_acquire_slot())
    if code is not None:
        return code

    # 面板强关后仍在跑的装卸任务，随主窗事件循环浮出续显
    from ._plugin import rearm_detached

    rearm_detached()

    from bot import Main

    return Main().main()
