# src/gui/mediator.py
"""GUI 中介者（内部实现）

- 定义 GUI 与 Bot 的通信协议
- 提供跨线程屏障与关闭竞态协调
"""

import threading

from PySide6.QtCore import QObject, Signal

from .signal import SafeSignal


class GUIBridge(QObject):
    """GUI 与 Bot 通信桥梁"""

    # ==================== 真实信号声明（元类注册，槽彼此隔离） ====================

    _signal_request_shutdown = Signal()
    _signal_request_shutdown_cancel = Signal()
    _signal_request_force_setup = Signal(object)  # {配置键: 错误文案}
    _signal_config_saved = Signal()
    _signal_request_exit = Signal(object)  # 携带请求退出的来源窗口，可为 None
    _signal_request_fatal = Signal(str)  # 致命错误：携带展示文案
    _signal_config_ready_changed = Signal(bool)  # 配置就绪状态变更
    _signal_config_verified = Signal()  # 配置校验刚通过（诊断窗原地刷绿用）

    # ==================== 防重连包装（对外的连接/发射入口） ====================

    # GUI 请求退出，Bot 收到后开始清理
    request_shutdown = SafeSignal()

    # GUI 取消退出，Bot 复位关闭状态
    request_shutdown_cancel = SafeSignal()

    # 请求打开强制配置窗口（参数：{配置键: 上次验证失败文案}）
    request_force_setup = SafeSignal()
    config_saved = SafeSignal()  # 配置窗口保存

    # 请求走完整退出流程（向导退出按钮用，携带来源窗口作确认框父级）
    request_exit = SafeSignal()

    # 致命错误：GUI 弹出提示窗，用户确认后退出进程
    request_fatal = SafeSignal()

    # 配置就绪状态变更：True 表示加载并验证通过，False 表示加载中或重验中
    config_ready_changed = SafeSignal()

    # 配置校验刚通过：诊断窗据此原地把通道行刷成可达，免重跑探测
    config_verified = SafeSignal()

    # ==================== 跨线程同步屏障 ====================

    # Bot 清理完毕，放行 GUI 关闭
    shutdown_completed_event = threading.Event()

    # ==================== 跨流程协调标志 ====================

    # 关闭流程进行中：阻止强制配置弹窗在关闭确认期间被打开
    _is_shutdown_pending: bool = False

    def is_shutdown_pending(self) -> bool:
        """查询关闭流程是否进行中"""
        return self._is_shutdown_pending

    def set_shutdown_pending(self, pending: bool) -> None:
        """标记/解除关闭流程"""
        self._is_shutdown_pending = pending


gui_bridge = GUIBridge()  # 全局单例实例化
