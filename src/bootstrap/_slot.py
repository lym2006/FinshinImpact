# src/bootstrap/_slot.py
"""启动资格裁决

- 引导锁内完成实例身份选择与实例锁抢占
- 非正常启动结果分流善后并给出退出码
- 抢到实例锁才导入主程序，路径常量随身份冻结
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

    - 值仅表意不参与比较运算
    """

    RUN = 0
    CANCEL = 1
    CONFLICT = 2
    PICKER_BUSY = 3


def _acquire_slot() -> _SlotResult:
    """取得本实例的启动资格

    - 引导锁内完成选身份与抢实例锁，两锁无缝衔接不留空档
    - 空档内重复启动会绕过实例锁，同账号双开互踩 Telegram 长轮询
    - 引导锁被占说明已有选择窗在开，本进程直接退，不重复弹窗
    - 选窗关闭即释放引导锁，让运行期间双击启动器仍能开新的选择窗
    """
    if get_profile():
        # 预设身份：不弹选窗，无需引导锁，仅抢实例锁防同账号双开
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
        if not acquire_instance_lock():
            return _SlotResult.CONFLICT
        return _SlotResult.RUN
    finally:
        release_bootstrap_lock()


def _popup(title_text: str, body: str, *, icon_warning: bool = True) -> None:
    """提示弹窗

    - 延迟导入：选窗模块与图标仅在需要弹窗时才付出加载代价
    """
    from PySide6.QtWidgets import QMessageBox

    from app_icon import ensure_app

    ensure_app()
    box = QMessageBox()
    box.setIcon(
        QMessageBox.Icon.Warning if icon_warning else QMessageBox.Icon.Information
    )
    box.setWindowTitle(title_text)
    box.setText(body)
    box.exec()


def _handle(result: _SlotResult) -> int | None:
    """非 RUNNING 结果的善后

    - 返回退出码，RUNNING 返回 None 交调用方继续启动
    - 选窗取消静默退
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

    - 抢锁与取消分流善后后，拿到实例锁才 import 主程序
    - 路径常量随身份冻结，须晚于身份码落环境变量
    """
    code = _handle(_acquire_slot())
    if code is not None:
        return code

    from bot import Main

    return Main().main()
