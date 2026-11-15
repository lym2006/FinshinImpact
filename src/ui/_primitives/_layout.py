"""布局边距与重灌

- 四边同值的边距、拆干净再重灌、滚动容器三种摆法只在这一处
"""

from PySide6.QtWidgets import QLayout, QScrollArea, QWidget

# Qt 布局四边
_EDGES = 4


def set_margins(layout: QLayout, pad: int, *, bottom: int | None = None) -> None:
    """四边摆同一个边距，给了 bottom 即只换底边"""
    sides = [pad] * _EDGES
    if bottom is not None:
        sides[-1] = bottom
    layout.setContentsMargins(*sides)


def clear_layout(layout: QLayout) -> None:
    """拆掉上一轮摆的控件，防重绘留残块

    - 布局本身留着，容器由调用方处置
    """
    while layout.count():
        item = layout.takeAt(0)
        if item is None:
            break
        widget = item.widget()
        if widget is None:
            continue
        widget.setParent(None)
        widget.deleteLater()


def make_scroller(inner: QWidget) -> QScrollArea:
    """把一块内容装进滚动区"""
    scroller = QScrollArea()
    scroller.setWidget(inner)
    scroller.setWidgetResizable(True)
    return scroller
