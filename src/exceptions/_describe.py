"""异常文案查询

- 七族文案表合成一张查找表
- 模板要的字段异常上没有即退回模板原文
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

    - 沿继承链往上找最近的一句文案
    - 表里没有即报异常类名
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
