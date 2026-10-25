# src/core/domain/config/_shared.py
"""全平台一致的配置段

- 定义 global、ai、chore、data 四个共享段字段表
"""

from ._models import ConfigKey, ConfigSection, FieldSpec, SectionSpec

# 全局
_GLOBAL_SECTION = SectionSpec(
    section=ConfigSection.GLOBAL,
    fields=(
        FieldSpec(
            section=ConfigSection.GLOBAL,
            key=ConfigKey.NETWORK_TIMEOUT,
            value_type=float,
            default=90.0,
            bounds=(1.0, 600.0),
        ),
    ),
)

# AI 配置
_AI_SECTION = SectionSpec(
    section=ConfigSection.AI,
    fields=(
        FieldSpec(
            section=ConfigSection.AI,
            key=ConfigKey.API_KEY,
            value_type=str,
            default="",
            required=True,
        ),
        FieldSpec(
            section=ConfigSection.AI,
            key=ConfigKey.TEMPERATURE,
            value_type=float,
            default=0.7,
            bounds=(0.0, 2.0),  # OpenAI 兼容规范
        ),
    ),
)

# 杂项
_CHORE_SECTION = SectionSpec(
    section=ConfigSection.CHORE,
    fields=(
        FieldSpec(
            section=ConfigSection.CHORE,
            key=ConfigKey.OWNER,
            value_type=str,
            default="",
            required=True,
        ),
        FieldSpec(
            section=ConfigSection.CHORE,
            key=ConfigKey.TRIGGERS,
            value_type=list,
            default=[],
            required=True,
        ),
    ),
)

# 数据维护
_DATA_SECTION = SectionSpec(
    section=ConfigSection.DATA,
    fields=(
        FieldSpec(
            section=ConfigSection.DATA,
            key=ConfigKey.RECORD_KEEP,
            value_type=float,
            default=30.0,
            bounds=(1.0, 3650.0),
        ),
        FieldSpec(
            section=ConfigSection.DATA,
            key=ConfigKey.WAITING,
            value_type=float,
            default=0.5,
            bounds=(0.1, 720.0),
        ),
    ),
)

# 共享配置段
SHARED_SECTIONS = (_GLOBAL_SECTION, _AI_SECTION, _CHORE_SECTION, _DATA_SECTION)
