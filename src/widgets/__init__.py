# src/widgets/__init__.py
"""共用 UI 组件包

- 代发跨包共用的应用实例工厂、弹窗基类、自绘勾选框、通用弹窗与计时泵
"""

from ._app import ensure_app
from ._base import BaseDialog
from ._check import TickedCheckBox
from ._factory import ButtonStyle, make_button, make_combo
from ._list import ThemedList
from ._notice import NoticeDialog
from ._shutdown import ShutdownDialog
from ._ticker import Ticker
from ._wait import WaitDialog

__all__ = [
    # 应用实例
    "ensure_app",
    # 弹窗基类
    "BaseDialog",
    # 控件
    "TickedCheckBox",
    "ThemedList",
    # 按钮
    "ButtonStyle",
    "make_button",
    "make_combo",
    # 通用弹窗
    "NoticeDialog",
    "WaitDialog",
    "ShutdownDialog",
    # 计时泵
    "Ticker",
]
