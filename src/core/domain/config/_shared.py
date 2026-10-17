# src/core/domain/config/_shared.py
"""全平台一致的配置段

- 定义 global、ai、chore、data 四个共享段字段表
"""

from ._models import ConfigKey, ConfigSection, FieldSpec, SectionSpec

# 人格设定默认正文，四行短正文与 assets/persona.example.md 完整人设不是同一段
_PERSONALITY_DEFAULT = (
    "重要：若无必要，只能使用简体中文和英语，优先使用用户的语言。\n"
    "使用Markdown格式回复，严禁使用与Markdown语法冲突的字符。\n"
    "在表达情绪、强调重点或增加可读性时，请适量使用emoji。\n"
    "再次强调：不要随意编造你的身份和能力。"
)

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
        FieldSpec(
            section=ConfigSection.CHORE,
            key=ConfigKey.USE_FILE,
            value_type=bool,
            default=True,
        ),
        FieldSpec(
            section=ConfigSection.CHORE,
            key=ConfigKey.PERSONALITY,
            value_type=str,
            default=_PERSONALITY_DEFAULT,
        ),
    ),
)

_DATA_SECTION = SectionSpec(
    section=ConfigSection.DATA,
    fields=(
        FieldSpec(
            section=ConfigSection.DATA,
            key=ConfigKey.CLEARUP,
            value_type=float,
            default=6.0,
            bounds=(0.1, 720.0),
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

SHARED_SECTIONS = (_GLOBAL_SECTION, _AI_SECTION, _CHORE_SECTION, _DATA_SECTION)
