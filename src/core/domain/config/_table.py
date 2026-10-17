# src/core/domain/config/_table.py
"""按平台拼装配置段全表

- 定义各平台的段序列，顺序即面板页签顺序
"""

from .._platform import Platform
from ._models import SectionSpec
from ._qq import QQ_SECTIONS
from ._shared import SHARED_SECTIONS
from ._tg import PROXY_SECTION

SECTIONS_BY_PLATFORM: dict[Platform, tuple[SectionSpec, ...]] = {
    Platform.TELEGRAM: (PROXY_SECTION, *SHARED_SECTIONS),
    Platform.QQ: (*SHARED_SECTIONS, *QQ_SECTIONS),
}
