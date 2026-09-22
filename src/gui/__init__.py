# src/gui/__init__.py
"""GUI 门面包

- 提供 BotGUI 类型与装配入口
"""

from utils.logger import GUI_FORMATTER, get_logger

from ._main_window import BotGUI
from ._qss import build_global_qss
from ._theme import BODY, FONT, TOOLBAR, TOOLBAR_BUTTONS, WINDOW
from .controllers import BaseController, build_controllers

logger = get_logger("GUI")

__all__ = [
    # 类型
    "BotGUI",
    # 唯一创建和初始化 GUI 方法
    "create_gui",
]


def create_gui() -> tuple[BotGUI, dict[str, BaseController]]:
    """创建并装配 BotGUI 实例"""
    botgui = BotGUI(
        qss=build_global_qss(),
        buttons=TOOLBAR_BUTTONS,
        configs=(FONT, WINDOW, BODY, TOOLBAR),
        formatter=GUI_FORMATTER,
    )

    # ==================== 打包业务控制器 ====================

    controllers, instances = build_controllers(botgui)

    # ==================== 防呆校验 ====================

    valid_ui_keys = {key for _, key in TOOLBAR_BUTTONS}
    registered_keys = {btn_id.replace("btn_", "", 1) for btn_id, _ in controllers}

    if unregistered := registered_keys - valid_ui_keys:
        raise ValueError(
            f"控制器绑定失败: 发现未在 UI 层定义的按钮标识 -> {unregistered}"
        )

    if missing := valid_ui_keys - registered_keys:
        raise ValueError(
            f"控制器缺失: UI 层定义了按钮，但缺少对应的 Controller -> {missing}"
        )

    # ==================== 注入依赖并返回 ====================

    botgui.set_action_map(dict(controllers))
    botgui.set_logger_handler()

    # 将实例列表转换为以 BTN_KEY 为键的字典，方便 Main 查找
    instance_map = {inst.BTN_KEY: inst for inst in instances}

    return botgui, instance_map
