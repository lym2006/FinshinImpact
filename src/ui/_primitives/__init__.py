"""视图公共件门面

- 代发构造工厂、自绘件、循环滚动的长文案标签、布局边距与窗层序工具
"""

from ._check import TickedCheckBox
from ._factory import fill_combo, make_button, make_combo
from ._layout import clear_layout, make_scroller, set_margins
from ._list import ThemedList
from ._marquee import MarqueeLabel
from ._stack import bring_front, follow_above

__all__ = [
    # 窗层序
    "bring_front",
    "follow_above",
    # 按钮与下拉
    "fill_combo",
    "make_button",
    "make_combo",
    # 布局边距与重灌
    "clear_layout",
    "make_scroller",
    "set_margins",
    # 列表、勾选框与文字
    "MarqueeLabel",
    "ThemedList",
    "TickedCheckBox",
]
