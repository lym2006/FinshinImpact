# src/ui/__init__.py
"""视图层门面

- 按属性惰性解析，取用哪个符号才 import 哪个子包
- 代发控件构造、生命周期件与通用弹窗
"""

import importlib
from typing import TYPE_CHECKING

_SYMBOL_MODULES = {
    "BaseDialog": "._dialogs",
    "NoticeDialog": "._dialogs",
    "ShutdownDialog": "._dialogs",
    "WaitDialog": "._dialogs",
    "ensure_app": "._lifecycle",
    "Ticker": "._lifecycle",
    "TickedCheckBox": "._primitives",
    "make_button": "._primitives",
    "make_combo": "._primitives",
    "ThemedList": "._primitives",
}

__all__ = [
    # 应用实例
    "ensure_app",
    # 弹窗基类
    "BaseDialog",
    # 控件
    "TickedCheckBox",
    "ThemedList",
    # 按钮
    "make_button",
    "make_combo",
    # 通用弹窗
    "NoticeDialog",
    "WaitDialog",
    "ShutdownDialog",
    # 计时泵
    "Ticker",
]

if TYPE_CHECKING:
    from ._dialogs import BaseDialog, NoticeDialog, ShutdownDialog, WaitDialog
    from ._lifecycle import Ticker, ensure_app
    from ._primitives import (
        ThemedList,
        TickedCheckBox,
        make_button,
        make_combo,
    )


def __getattr__(name: str) -> object:
    module_path = _SYMBOL_MODULES.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(module_path, __name__)
    return getattr(module, name)
