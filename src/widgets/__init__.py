# src/widgets/__init__.py
"""可复用 UI 组件包

- 代发跨包共用的弹窗基类、自绘勾选框与通用弹窗
- 转发供业务弹窗装配复用的共用样式片段
"""

from ._base import BaseDialog
from ._check import TickedCheckBox
from ._dialog_qss import (
    DIALOG_BASE_QSS,
    DIALOG_BUTTON_QSS,
    DIALOG_LABEL_QSS,
    WAIT_QSS,
)
from ._notice import NoticeDialog
from ._shutdown import ShutdownDialog
from ._wait import WaitDialog

__all__ = [
    # 弹窗基类
    "BaseDialog",
    # 控件
    "TickedCheckBox",
    # 通用弹窗
    "NoticeDialog",
    "WaitDialog",
    "ShutdownDialog",
    # 共用样式片段
    "DIALOG_BASE_QSS",
    "DIALOG_LABEL_QSS",
    "DIALOG_BUTTON_QSS",
    "WAIT_QSS",
]
