# src/ui/_dialogs/__init__.py
"""通用弹窗子包门面

- 代发弹窗基类与提示、等待、关闭确认三窗
"""

from ._base import BaseDialog
from ._notice import NoticeDialog
from ._shutdown import ShutdownDialog
from ._wait import WaitDialog

__all__ = [
    # 弹窗基类
    "BaseDialog",
    # 通用弹窗
    "NoticeDialog",
    "WaitDialog",
    "ShutdownDialog",
]
