# src/core/domain/config/_table.py
"""按平台拼装配置段全表

- 定义各平台的段序列，顺序即面板页签顺序
"""

from .._platform import Platform
from ._models import TabSpec
from ._qq import QQ_TABS
from ._shared import SHARED_TABS
from ._tg import PROXY_TAB

TABS_BY_PLATFORM: dict[Platform, tuple[TabSpec, ...]] = {
    Platform.TELEGRAM: (PROXY_TAB, *SHARED_TABS),
    Platform.QQ: (*SHARED_TABS, *QQ_TABS),
}
