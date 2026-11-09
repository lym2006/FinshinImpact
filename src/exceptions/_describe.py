# src/exceptions/_describe.py
"""异常文案查询

- 各族文案表摊成一张，按继承链找最近的一句
- 填参容错，模板要的字段异常上没有即退回模板原文
"""

from typing import Any

from ._adapter import ADAPTER_MAP
from ._config import CONFIG_MAP
from ._connectivity import CONNECTIVITY_MAP
from ._gui import GUI_MAP
from ._network import NETWORK_MAP
from ._plugins import PLUGINS_MAP
from ._version import VERSION_MAP

# 各族表的合集，键是异常类
_TEXTS: dict[type, str] = {}
for _table in (
    ADAPTER_MAP,
    CONFIG_MAP,
    CONNECTIVITY_MAP,
    GUI_MAP,
    NETWORK_MAP,
    PLUGINS_MAP,
    VERSION_MAP,
):
    _TEXTS.update(_table)


def describe_error(exc: BaseException) -> str:
    """取异常那句给人看的话

    - 沿继承链往上找，族里新加的子类没点名也能落到父类那一句
    - 表里一句都没有即报异常类名，细节归调试日志
    """
    attrs: dict[str, Any] = vars(exc)
    for cls in type(exc).__mro__:
        template = _TEXTS.get(cls)
        if template is None:
            continue
        try:
            return template.format(**attrs)
        except (KeyError, IndexError):
            return template
    return type(exc).__name__
