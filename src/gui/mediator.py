# src/gui/mediator.py
"""GUI 中介者

- 定义 GUI 与 Bot 的通信协议，信号按流向分组声明
- 提供跨线程屏障与关闭竞态协调
"""

import threading

from PySide6.QtCore import QObject

from .signal import SafeSignal


class GUIBridge(QObject):
    """GUI 与 Bot 通信桥梁"""

    # GUI → Bot：配置事件与关闭指令
    config_candidate = SafeSignal()  # 候选配置进内存待验，校验通过才落盘
    config_abort = SafeSignal()  # 中止在途校验，候选回退不触磁盘
    config_saved = SafeSignal()  # 配置已落盘，唤醒验证循环热重载
    request_shutdown = SafeSignal()  # 退出确认后发，Bot 停服务并清理放行
    request_shutdown_cancel = SafeSignal()  # 确认框取消，Bot 复位关闭状态

    # Bot → GUI：状态广播与弹窗调度
    config_ready_changed = SafeSignal(
        bool
    )  # 就绪态变更：True 验证通过，False 加载中或重验中
    verify_progress = SafeSignal(
        object
    )  # 校验进度帧，渲染校验表格窗：rows 整表 / id 单行
    request_force_setup = SafeSignal(
        object
    )  # 呼出强制配置向导并标红出错字段：{配置键: 错误文案}
    request_notice = SafeSignal(
        str, bool
    )  # 弹通知窗，致命确认后直退：(展示文案，是否致命)

    # GUI → GUI：退出入口
    request_exit = SafeSignal(
        object
    )  # 向导退出按钮/主窗关闭：只弹确认框，未确认不触 Bot

    # Bot 清理完毕，放行 GUI 关闭
    shutdown_completed_event = threading.Event()

    # 关闭流程进行中，阻止强制配置弹窗被打开
    _is_shutdown_pending: bool = False

    def is_shutdown_pending(self) -> bool:
        """查询关闭流程是否进行中"""
        return self._is_shutdown_pending

    def set_shutdown_pending(self, pending: bool) -> None:
        """标记/解除关闭流程"""
        self._is_shutdown_pending = pending


gui_bridge = GUIBridge()  # 全局单例实例化
