# src/ui/_primitives/__init__.py
"""哑控件子包门面

- 代发构造工厂、自绘件与循环滚动的长文案标签
"""

from ._check import TickedCheckBox
from ._factory import make_button, make_combo
from ._list import ThemedList
from ._marquee import MarqueeLabel

__all__ = [
    # 按钮
    "make_button",
    "make_combo",
    # 列表、勾选框与文字
    "MarqueeLabel",
    "ThemedList",
    "TickedCheckBox",
]
