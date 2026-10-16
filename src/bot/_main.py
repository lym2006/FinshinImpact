# src/bot/_main.py
"""主程序装配

- 建 GUI 与控制器，接通信号总线
- 起后台事件循环托管服务，退出时统一清理资源
"""

import asyncio
import threading
import time
from collections.abc import Callable
from concurrent.futures import Future
from typing import cast

from app_icon import ensure_app
from gui import BotGUI, create_gui
from gui.controllers import BaseController, SettingsController, ShutdownController
from gui.mediator import gui_bridge
from gui.theme import WINDOW
from messages import CheckMessage
from profile_env import get_profile
from utils import get_logger
from utils.check import preload_engine
from utils.lifecycle import shutdown_all

from ._managers import BotManager

# 退出清理
_LOOP_JOIN_TIMEOUT = 5  # 等事件循环线程退出最多 5 秒


class Main:
    """Bot 主程序"""

    def __init__(
        self,
        on_ready: Callable[[], None] | None = None,
        t0: float | None = None,
    ) -> None:
        self.logger = get_logger("Main")
        self._on_ready = on_ready
        self._t0 = t0 if t0 is not None else time.monotonic()
        self._loop = asyncio.new_event_loop()
        self._manager = BotManager(self._loop)
        self._bot_task: Future | None = None  # 跨线程完成句柄，非 asyncio 任务
        self._loop_thread: threading.Thread | None = None

    def main(self) -> int:
        """主函数"""
        try:
            # 实例锁由 bootstrap 统一抢占
            app = ensure_app()

            # 引擎重依赖已由引导层后台线程预热，此处命中缓存近乎零耗时
            preload_engine()

            window, instances = create_gui()

            # 多实例任务栏区分：标题带身份码，无身份码维持原标题
            profile = get_profile()
            if profile:
                window.setWindowTitle(f"{WINDOW.title} - {profile}")
            window.show()
            app.processEvents()

            # 主窗已就位，收起引导层的启动等待窗
            if self._on_ready is not None:
                self._on_ready()
            self.logger.info(
                CheckMessage.READY_COST.format(cost=time.monotonic() - self._t0)
            )
            self.logger.debug("GUI 加载完成")

            self._wire_signals(window, instances)

            # 启动后台线程
            loop_thread = threading.Thread(
                target=self._loop.run_forever,
                daemon=True,
                name="AsyncioLoop",
            )
            loop_thread.start()
            self._loop_thread = loop_thread

            # 启动 Manager：threadsafe 入口会唤醒 selector，裸 create_task 叫不醒
            self._bot_task = asyncio.run_coroutine_threadsafe(
                self._manager.start(), self._loop
            )
            self.logger.info("调度器启动完成")

            # 进入 Qt 主循环
            return app.exec()

        except Exception as e:
            self.logger.send_error("程序启动异常", e)
            return 1
        finally:
            self._cleanup()

    def _wire_signals(
        self, window: BotGUI, instances: dict[str, BaseController]
    ) -> None:
        """接通总线信号到 GUI 与 Manager"""
        # 获取控制器
        settings_controller = cast(SettingsController, instances.get("settings"))
        shutdown_controller = cast(ShutdownController, instances.get("shutdown"))
        window.set_shutdown_handler(shutdown_controller.shutdown_now)

        # 强制配置信号：投递到 GUI 线程，呼出 SETUP 面板
        gui_bridge.request_force_setup.connect(
            settings_controller.show_setup_dialog, "强制配置", queued=True
        )

        # 配置保存信号：唤醒验证循环或触发热重载
        gui_bridge.config_saved.connect(self._manager.on_config_saved, "配置唤醒")

        # 候选校验信号：候选已在内存，通过才落盘
        gui_bridge.config_candidate.connect(
            self._manager.on_config_candidate, "候选唤醒"
        )

        # 取消校验信号：中止在途校验并回退候选
        gui_bridge.config_abort.connect(self._manager.on_config_abort, "取消校验")

        # 关闭请求信号：Manager 层统一处理服务停止与清理放行
        gui_bridge.request_shutdown.connect(
            self._manager.on_shutdown_request, "关闭唤醒"
        )

        # 取消关闭信号：Manager 复位，恢复响应配置事件
        gui_bridge.request_shutdown_cancel.connect(
            self._manager.on_shutdown_cancelled, "取消关闭"
        )

        # 通知弹窗：(文案, 是否致命) Queued 投递到 GUI 线程，致命确认后直退
        gui_bridge.request_notice.connect(window.show_notice, "通知弹窗", queued=True)

        # 向导内"退出程序"按钮：携带向导窗口，确认框以其为父级
        gui_bridge.request_exit.connect(
            shutdown_controller.request_exit_from, "弹窗退出"
        )

    def _cleanup(self) -> None:
        """统一清理资源

        - 停服务、清生命周期注册表、关事件循环
        """
        self._manager.stop_service()

        # 清理失败项以列表返回，由本层记录
        for item in shutdown_all():
            self.logger.error(f"清理失败: {item}")

        # close 拒绝 running 循环：先投递 stop，join 确认退出后再关
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=_LOOP_JOIN_TIMEOUT)
            if self._loop_thread.is_alive():
                self.logger.info(
                    f"事件循环线程未在 {_LOOP_JOIN_TIMEOUT} 秒内退出，跳过关闭"
                )
        if not self._loop.is_closed() and not self._loop.is_running():
            self._loop.close()

        self.logger.debug("资源已清理")
