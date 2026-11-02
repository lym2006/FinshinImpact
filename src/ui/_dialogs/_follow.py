# src/ui/_dialogs/_follow.py
"""自家两窗之间的常驻浮顶

- 系统层挂跟随关系，再盯住被跟窗的激活事件补上浮
- 只在自家窗之间排先后
"""

from typing import TYPE_CHECKING, cast
from weakref import WeakKeyDictionary

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    from ._check import CheckDialog

# 已挂上浮钩子的窗：随窗销毁即撤钩子，重复调用不叠第二层
_lifts: "WeakKeyDictionary[QWidget, QObject]" = WeakKeyDictionary()


class _LiftOnActivate(QObject):
    """被跟窗激活时的上浮钩子"""

    def __init__(self, top: "CheckDialog") -> None:
        super().__init__()
        self._top = top

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        """被跟窗拿到激活即浮回一次，不抢它的焦点"""
        if event.type() == QEvent.Type.WindowActivate:
            self._top.bring_front(False, cast("QWidget", watched))
        return super().eventFilter(watched, event)


def follow_above(top: "CheckDialog", owner: QWidget) -> None:
    """让一只窗常驻在另一只上面"""
    # 原生句柄要先具象，系统层才有关系可挂
    top.winId()
    owner.winId()
    top.windowHandle().setTransientParent(owner.windowHandle())
    lift = _lifts.get(owner)
    if lift is None:
        # 跟随关系对已可见的窗不当场生效，补一层激活上浮
        lift = _LiftOnActivate(top)
        _lifts[owner] = lift
        owner.installEventFilter(lift)
    top.bring_front(False, owner)
