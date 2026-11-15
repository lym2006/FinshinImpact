"""通用工具门面

- 按属性惰性解析，取用哪个符号才 import 哪个子包
- 只导出多消费方的基础符号
- 路径常量不走这层转发，各消费方直连 paths 取
"""

import importlib
from typing import TYPE_CHECKING

_SYMBOL_MODULES = {
    "config_manager": "._config_manager",
    "get_logger": ".logger",
    "register_lifecycle": ".lifecycle",
    "unregister_lifecycle": ".lifecycle",
}

__all__ = [
    # 基础服务
    "config_manager",
    "get_logger",
    # 生命周期
    "register_lifecycle",
    "unregister_lifecycle",
]

if TYPE_CHECKING:
    from ._config_manager import config_manager
    from .lifecycle import register_lifecycle, unregister_lifecycle
    from .logger import get_logger


def __getattr__(name: str) -> object:
    module_path = _SYMBOL_MODULES.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(module_path, __name__)
    return getattr(module, name)
