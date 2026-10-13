# src/theme/__init__.py
"""公共视觉包

- 代发跨层共用的调色板、自绘控件与输出字体加载
"""

from ._check import TickedCheckBox
from ._font import load_font
from ._palette import PALETTE

__all__ = [
    # 调色板
    "PALETTE",
    # 控件
    "TickedCheckBox",
    # 字体
    "load_font",
]
