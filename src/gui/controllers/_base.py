# src/gui/controllers/_base.py
"""控制器基类（内部实现）

- 定义按钮绑定契约与执行入口
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

from utils.logger import get_logger

from ._decorator import gui_guard

if TYPE_CHECKING:
    from gui import BotGUI


class BaseController(ABC):
    """控制器基类

    统一 GUI 引用与日志注入，强制子类声明按钮契约。
    """

    # ==================== 契约声明区 ====================

    # 子类必须声明这两个属性，否则实例化时会报错

    LOGGER_NAME: ClassVar[str]  # 日志器名称
    BTN_KEY: ClassVar[str]  # 绑定的按钮标识（如 "func"，底层会自动拼接为 "btn_func"）

    @abstractmethod
    def _execute(self) -> None:
        """业务逻辑入口

        子类必须实现，否则实例化抛 TypeError。
        """

    # ==================== 初始化与生命周期 ====================

    def __init__(self, gui_ref: "BotGUI") -> None:
        self.gui = gui_ref
        self.logger = get_logger(self.LOGGER_NAME)

    # ==================== 自动生成的绑定标识 ====================

    @property
    def btn_id(self) -> str:
        """完整按钮 ID"""
        return f"btn_{self.BTN_KEY}"

    # ==================== 公开业务执行入口 ====================

    @gui_guard
    def execute(self) -> None:
        """业务执行入口

        触发安全守卫后委托 _execute()。
        """
        self._execute()
