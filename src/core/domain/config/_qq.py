# src/core/domain/config/_qq.py
"""QQ 专属配置段

- 适配器未接线，本轮无专属字段
- 段名与键待 OneBot 连接参数定案后补入
"""

from ._models import TabSpec

QQ_TABS: tuple[TabSpec, ...] = ()
