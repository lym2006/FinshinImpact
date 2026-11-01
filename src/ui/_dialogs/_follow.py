# src/ui/_dialogs/_follow.py
"""自家两窗之间的常驻浮顶

- 系统层挂跟随关系，再盯住被跟窗的激活事件补上浮
- 只在自家窗之间排先后，不借跨应用置顶
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
    """被跟窗一动就把上面那只窗提回来

    - 只盯激活事件，其余事件原样放行
    """

    def __init__(self, top: "CheckDialog") -> None:
        super().__init__()
        self._top = top

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        """被跟窗拿到激活即浮回一次，不抢它的焦点"""
        if event.type() == QEvent.Type.WindowActivate:
            self._top.bring_front(False, cast("QWidget", watched))
        return super().eventFilter(watched, event)


def follow_above(top: "CheckDialog", owner: QWidget) -> None:
    """让 top 常驻在 owner 上面，只排先后不抢焦点

    - 可见窗改跟随关系不当场生效，故再加一层激活上浮
    - 句柄需 winId 强制具象，QWindow 层才有关系可挂
    """
    top.winId()
    owner.winId()
    top.windowHandle().setTransientParent(owner.windowHandle())
    lift = _lifts.get(owner)
    if lift is None:
        lift = _LiftOnActivate(top)
        _lifts[owner] = lift
        owner.installEventFilter(lift)
    top.bring_front(False, owner)
