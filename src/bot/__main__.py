# src/bot/__main__.py
"""Bot 启动主模块

- 提供 GUI 构建、服务总控与资源清理入口
"""

import asyncio
import sys
import threading
from concurrent.futures import Future
from typing import cast

from PySide6.QtWidgets import QApplication, QMessageBox

from gui import create_gui
from gui._theme import GLOBAL, WINDOW
from gui.controllers import SettingsController, ShutdownController
from gui.mediator import gui_bridge
from utils import acquire_instance_lock, get_logger
from utils.lifecycle import shutdown_all

from ._managers import BotManager


class Main:
    """Bot 主程序"""

    def __init__(self) -> None:
        self.logger = get_logger("Main")
        self._loop = asyncio.new_event_loop()
        self._manager = BotManager(self._loop)
        self._bot_task: Future | None = None  # 跨线程完成句柄，非 asyncio 任务
        self._loop_thread: threading.Thread | None = None

    def main(self) -> int:
        """主函数"""
        try:
            # 0. 单实例守卫：同目录双开会互踩配置与数据，先到先得
            if not acquire_instance_lock():
                app = QApplication(sys.argv)
                QMessageBox.warning(None, WINDOW.title, GLOBAL.already_running)
                return 0

            # 1. 启动 GUI
            app = QApplication(sys.argv)
            window, instances = create_gui()
            window.show()
            app.processEvents()
            self.logger.debug("GUI 加载完成")

            # 2. 获取控制器并绑定信号
            settings_controller = cast(SettingsController, instances.get("settings"))
            shutdown_controller = cast(ShutdownController, instances.get("shutdown"))
            window.set_shutdown_handler(shutdown_controller.shutdown_now)

            # 强制配置信号：投递到 GUI 线程，呼出 SETUP 面板
            gui_bridge.request_force_setup.connect(
                settings_controller.show_setup_dialog, "强制配置", queued=True
            )

            # 配置保存信号：唤醒验证循环或触发热重载
            gui_bridge.config_saved.connect(self._manager.on_config_saved, "配置唤醒")

            # 关闭请求信号：Manager 层统一处理服务停止与清理放行
            gui_bridge.request_shutdown.connect(
                self._manager.on_shutdown_request, "关闭唤醒"
            )

            # 取消关闭信号：Manager 复位，恢复响应配置事件
            gui_bridge.request_shutdown_cancel.connect(
                self._manager.on_shutdown_cancelled, "取消关闭"
            )

            # 致命错误信号：Queued 投递到 GUI 线程
            gui_bridge.request_fatal.connect(window.show_fatal, "致命错误", queued=True)

            # 向导内"退出程序"按钮：携带向导窗口，确认框以其为父级
            gui_bridge.request_exit.connect(
                shutdown_controller.request_exit_from, "弹窗退出"
            )

            # 3. 启动后台线程
            loop_thread = threading.Thread(
                target=self._loop.run_forever,
                daemon=True,
                name="AsyncioLoop",
            )
            loop_thread.start()
            self._loop_thread = loop_thread

            # 4. 启动 Manager：threadsafe 入口会唤醒 selector，裸 create_task 叫不醒
            self._bot_task = asyncio.run_coroutine_threadsafe(
                self._manager.start(), self._loop
            )
            self.logger.info("调度器启动完成")

            # 5. 进入 Qt 主循环
            return app.exec()

        except Exception as e:
            self.logger.send_error("程序启动异常", e)
            return 1
        finally:
            self._cleanup()

    # ==================== 清理 ====================

    def _cleanup(self) -> None:
        """统一清理资源

        停服务、清生命周期注册表、关事件循环。
        """
        self._manager.stop_service()

        # 清理失败项以列表返回，由本层记录
        for item in shutdown_all():
            self.logger.error(f"清理失败: {item}")

        # close 拒绝 running 循环：先投递 stop，join 确认退出后再关
        if self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._loop_thread and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=5)
            if self._loop_thread.is_alive():
                self.logger.info("事件循环线程未在 5 秒内退出，跳过关闭")
        if not self._loop.is_closed() and not self._loop.is_running():
            self._loop.close()

        self.logger.debug("清理完成")


if __name__ == "__main__":
    sys.exit(Main().main())
