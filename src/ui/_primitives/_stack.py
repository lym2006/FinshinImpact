# src/ui/_primitives/_stack.py
"""自家窗之间的层序

- 提顶要看的三个条件收在这一处
- 系统层挂跟随关系，再盯住被跟窗的激活事件补上浮
"""

from typing import cast
from weakref import WeakKeyDictionary

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication, QWidget

# 已挂上浮钩子的窗：随窗销毁即撤钩子，重复调用不叠第二层
_lifts: "WeakKeyDictionary[QWidget, QObject]" = WeakKeyDictionary()


class _LiftOnActivate(QObject):
    """被跟窗激活时的上浮钩子"""

    def __init__(self, top: QWidget) -> None:
        super().__init__()
        self._top = top

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        """被跟窗拿到激活即浮回一次，不抢它的焦点"""
        if event.type() == QEvent.Type.WindowActivate:
            bring_front(self._top, False, cast(QWidget, watched))
        return super().eventFilter(watched, event)


def bring_front(
    win: QWidget, grab_focus: bool = True, owner: QWidget | None = None
) -> None:
    """把一只窗提到本程序窗口最前

    - 藏着的窗不参与排序，提它没意义
    - 有别的模态窗开着就让位，免得抢走它正在收的输入
    - 被跟的那只窗自己模态不算拦路，照样提顶
    - 只排序不抢焦点填 False：向导里正在打字，不该被浮顶打断
    """
    modal = QApplication.activeModalWidget()
    if not win.isVisible() or (modal is not None and modal is not owner):
        return
    win.raise_()
    if grab_focus:
        win.activateWindow()


def follow_above(top: QWidget, owner: QWidget) -> None:
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
    bring_front(top, False, owner)
