# src/bootstrap/_slot.py
"""启动资格判定

- 引导锁内完成实例身份选择与实例锁抢占
- 非正常启动结果分别提示并给出退出码
- 抢到实例锁才导入主程序，路径常量在导入期随身份码确定
- utils 与引擎重依赖后台线程导入，主线程全程泵事件让提示卡秒表连走
"""

import importlib
import threading
import time
from enum import IntEnum

from system.instance_lock import (
    acquire_bootstrap_lock,
    acquire_instance_lock,
    release_bootstrap_lock,
)
from system.profile_env import get_profile, set_profile

# 主程序 GUI 装配链，分步导入时逐模块各泵一轮
_GUI_MODULES = ("ui._windows", "ui._bridge")

# utils 后台导入落位后放行主线程续导 GUI 链
_UTILS_READY = threading.Event()

# 等后台导入落位的轮询步长，泵够密秒表才看得出在走
_JOIN_PUMP_S = 0.2


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

        # 启用集变动此刻结算，缺库补装装完才起，装失败禁用相关插件
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

    from skin.qss import build_bootstrap_qss
    from ui import ensure_app

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
        from skin.messages import PickerMessage

        _popup(PickerMessage.TITLE, PickerMessage.BUSY, icon_warning=False)
        return 0

    from skin.theme import GLOBAL, WINDOW

    _popup(WINDOW.title, GLOBAL.already_running)
    return 0


def _pump() -> None:
    """泵一轮事件让提示卡应答重绘

    - 排除用户输入，半初始化界面收不到点击
    - 秒表与重绘全靠本函数泵出，泵点越密跳秒越顺
    """
    from PySide6.QtCore import QCoreApplication, QEventLoop

    QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)


def _preload_engine_async() -> threading.Thread:
    """后台线程导入 utils 并预热引擎链

    - utils 落位即发信号，主线程泵到信号才续导依赖它的 GUI 链
    """
    # utils 与 aiogram 冷盘会被杀软逐文件扫描，主线程泵不动
    # 两者的导入不绑定线程，才放到子线程执行
    thread = threading.Thread(
        target=_preload_engine_worker,
        daemon=True,
        name="EnginePreload",
    )
    thread.start()
    return thread


def _preload_engine_worker() -> None:
    """子线程里付 utils 与引擎导入费

    - utils 先落位发信号，导入失败也放行，交主线程兜底重导
    """
    try:
        importlib.import_module("utils")
    except Exception:  # noqa: BLE001  预热失败交主线程兜底重导
        pass
    finally:
        _UTILS_READY.set()
    try:
        from utils.check import preload_engine

        preload_engine()
    except Exception:  # noqa: BLE001  预热失败交主线程兜底重导
        pass


def _wait_preload(thread: threading.Thread) -> None:
    """泵着等预热线程收尾，等待期秒表照常逐秒走"""
    while thread.is_alive():
        thread.join(_JOIN_PUMP_S)
        _pump()
    _pump()


def _pump_imports() -> threading.Thread:
    """后台预热打底，主线程分步导入装配链并步间泵事件

    - utils 与引擎交后台线程，主线程泵到 utils 落位才续导 GUI 链
    - GUI 链与 aiogram 预热并行，拆步顺序与 bot._main 顶层导入对齐
    - preload_engine 幂等，Main.main 内原调用兜底
    """
    preload = _preload_engine_async()
    while not _UTILS_READY.is_set():
        _UTILS_READY.wait(_JOIN_PUMP_S)
        _pump()
    for name in _GUI_MODULES:
        importlib.import_module(name)
        _pump()
    importlib.import_module("bot._managers")
    _pump()
    return preload


def main() -> int:
    """引导入口

    - 完成资格判定后，持锁进程才导入主程序
    - 须先写入身份码环境变量，再导入路径常量
    - 导入主程序前先弹提示卡
    """
    code = _handle(_acquire_slot())
    if code is not None:
        return code

    from ._picker import show_launch_wait
    from ._warmup import start_warmup

    t0 = time.monotonic()

    # 主程序导入完成前有无窗空白期，提示卡垫住这段
    wait = show_launch_wait(get_profile())

    def on_ready() -> None:
        """主窗就绪，收起提示卡并预热字节码"""
        wait.close()
        start_warmup()

    preload = _pump_imports()
    _wait_preload(preload)
    from bot import Main

    try:
        return Main(on_ready=on_ready, t0=t0).main()
    finally:
        wait.close()
