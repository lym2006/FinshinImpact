# src/core/domain/config/_qq.py
"""QQ 专属配置段

- 定义 QQ 平台的配置段字段表
- 适配器未接线，段表为空
"""

from ._models import SectionSpec

QQ_SECTIONS: tuple[SectionSpec, ...] = ()
