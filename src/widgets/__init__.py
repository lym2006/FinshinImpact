# src/widgets/__init__.py
"""可复用 UI 组件包

- 代发跨包共用的弹窗基类与自绘勾选框
"""

from ._base import BaseDialog
from ._check import TickedCheckBox

__all__ = [
    # 弹窗基类
    "BaseDialog",
    # 控件
    "TickedCheckBox",
]
