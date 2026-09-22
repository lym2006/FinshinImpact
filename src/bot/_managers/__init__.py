# src/bot/_managers/__init__.py
"""Bot 管理器门面（内部实现）

- 定义总控入口与 GUI 信号接入点
- 实现子管理器协调：初始化→校验→启动/热重载
"""

import asyncio
from collections.abc import Callable

from gui.mediator import gui_bridge
from utils import config_manager, get_logger

from ..error_guard import error_guard
from ._initialization import InitializationManager
from ._service import ServiceManager
from ._settings import SettingsManager

__all__ = ["BotManager"]


class BotManager:
    """Bot 业务管理器"""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        if hasattr(self, "_is_initialized") and self._is_initialized:
            return
        self._is_initialized = True
        self._logger = get_logger("Manager")
        self._loop = loop

        self._initializer = InitializationManager()
        self._service_manager = ServiceManager(self._get_config_func)
        self._settings_manager = SettingsManager(self._get_raw_config_func)

        # 以下状态仅在 asyncio 线程读写（线程封闭）
        self._shutdown = False
        self._apply_task: asyncio.Task[None] | None = None
        # 最近一次生效并重启过引擎的参数指纹：一致则跳过重启防闪断
        self._last_applied: tuple[str, str, float] | None = None
        # 三级解析出的生效通道；引擎与指纹均以此为准
        self._resolved_proxy: str | None = None

    # ==================== 对外启停与信号处理（Qt 线程入口） ====================

    @error_guard("Bot 启动", catch_all=True)
    async def start(self) -> None:
        """启动服务"""
        await self._initializer.execute()
        await self._apply_config()

    def on_config_saved(self) -> None:
        """配置保存回调（Qt 侧投递）"""
        self._loop.call_soon_threadsafe(self._handle_config_saved)

    def on_shutdown_request(self) -> None:
        """关闭请求回调（Qt 侧投递）"""
        self._loop.call_soon_threadsafe(self._handle_shutdown)

    def on_shutdown_cancelled(self) -> None:
        """取消关闭回调（Qt 侧投递）"""
        self._loop.call_soon_threadsafe(self._handle_shutdown_cancel)

    def stop_service(self) -> None:
        """停止

        关闭服务，清理资源
        """
        self._service_manager.stop_service()

    # ==================== 信号处理（asyncio 线程执行） ====================

    def _handle_config_saved(self) -> None:
        """重新校验并应用配置

        仅 loop 线程。
        """
        if self._shutdown:
            self._logger.info("关闭流程中忽略配置保存事件")
            return
        if self._apply_task is not None and not self._apply_task.done():
            self._logger.debug("上一次配置应用尚未完成，跳过本次触发")
            return
        self._apply_task = self._loop.create_task(self._apply_config())

    def _handle_shutdown_cancel(self) -> None:
        """在 loop 线程复位关闭标志"""
        if self._shutdown:
            self._logger.info("关闭已取消，恢复配置事件响应")
            self._shutdown = False

    def _handle_shutdown(self) -> None:
        """停止服务并放行 GUI 退出"""
        self._logger.info("Manager 收到关闭请求")
        self._shutdown = True
        if self._apply_task is not None and not self._apply_task.done():
            self._apply_task.cancel()
        self.stop_service()
        gui_bridge.shutdown_completed_event.set()

    # ==================== 配置应用统一入口 ====================

    @error_guard("配置校验")
    async def _apply_config(self) -> None:
        """应用当前配置

        失败弹向导等待再次保存，通过则重启服务
        """
        if self._shutdown:
            return
        # 重验期间先收回就绪，阻止 EDIT 弹窗读到半新半旧的配置
        gui_bridge.config_ready_changed.emit(False)
        await self._settings_manager.execute()
        if not await self._settings_manager.verify_connectivity():
            self._resolved_proxy = None
            # 保持不就绪：数据修复完成前 EDIT 一律拦截
            self._request_setup(self._settings_manager.last_errors)
            return
        # 生效通道接引擎：配置不通时自动落到系统代理/直连
        self._resolved_proxy = self._settings_manager.resolved_proxy
        # 配置已加载且验证通过（数据先就位，最后广播）
        gui_bridge.config_ready_changed.emit(True)
        try:
            token, proxy = self._get_config_func()
            fingerprint = (
                token,
                proxy,
                config_manager.get("global.network_timeout", float),
            )
        except Exception:  # 参数不可得：不做跳过优化，照常重启
            fingerprint = None
        if fingerprint is not None and self._last_applied == fingerprint:
            # 生效通道与引擎参数未变：验证通过即复用，不闪断重启
            self._logger.info("配置验证通过，运行参数未变，跳过重启")
            return
        self.stop_service()
        await self._service_manager.execute()
        self._last_applied = fingerprint
        self._logger.info("配置验证通过，服务运行中")

    def _request_setup(self, field_errors: dict[str, str] | None = None) -> None:
        """弹出强制配置向导"""
        self._logger.info("检测到配置有误，弹出配置向导...")
        gui_bridge.request_force_setup.emit(field_errors or {})

    # ==================== 辅助方法 ====================

    def _get_config_func(self) -> tuple[str, str]:
        """读取 Token 与生效 Proxy（引擎与指纹专用）

        三级解析通过后引擎走 resolved 通道；未校验时退回配置原值。
        """
        token, cfg = self._get_raw_config_func()
        if self._resolved_proxy is not None:
            return token, self._resolved_proxy
        return token, cfg

    def _get_raw_config_func(self) -> tuple[str, str]:
        """读取配置文件原值（校验专用）

        不得混入解析通道：否则通道自我反馈，下次校验把生效通道
        当成配置值，"生效通道 配置代理"之类的标签就成了谎报。
        """
        get: Callable[[str, type], str] = config_manager.get
        return get("basic.telegram_token", str), get("basic.proxy", str).strip()
