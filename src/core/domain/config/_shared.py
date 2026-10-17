# src/core/domain/config/_shared.py
"""全平台一致的配置段

- 定义 global、ai、chore、data 四个共享段字段表
"""

from ._models import ConfigKey, ConfigNamespace, FieldSpec, TabSpec

# 人格设定默认正文，四行短正文与 assets/persona.example.md 完整人设不是同一段
_PERSONALITY_DEFAULT = (
    "重要：若无必要，只能使用简体中文和英语，优先使用用户的语言。\n"
    "使用Markdown格式回复，严禁使用与Markdown语法冲突的字符。\n"
    "在表达情绪、强调重点或增加可读性时，请适量使用emoji。\n"
    "再次强调：不要随意编造你的身份和能力。"
)

_GLOBAL_TAB = TabSpec(
    namespace=ConfigNamespace.GLOBAL,
    fields=(
        FieldSpec(
            namespace=ConfigNamespace.GLOBAL,
            key=ConfigKey.NETWORK_TIMEOUT,
            value_type=float,
            default=90.0,
            bounds=(1.0, 600.0),
        ),
    ),
)

_AI_TAB = TabSpec(
    namespace=ConfigNamespace.AI,
    fields=(
        FieldSpec(
            namespace=ConfigNamespace.AI,
            key=ConfigKey.API_KEY,
            value_type=str,
            default="",
            required=True,
        ),
        FieldSpec(
            namespace=ConfigNamespace.AI,
            key=ConfigKey.TEMPERATURE,
            value_type=float,
            default=0.7,
            bounds=(0.0, 2.0),  # OpenAI 兼容规范
        ),
    ),
)

_CHORE_TAB = TabSpec(
    namespace=ConfigNamespace.CHORE,
    fields=(
        FieldSpec(
            namespace=ConfigNamespace.CHORE,
            key=ConfigKey.OWNER,
            value_type=str,
            default="",
            required=True,
        ),
        FieldSpec(
            namespace=ConfigNamespace.CHORE,
            key=ConfigKey.TRIGGERS,
            value_type=list,
            default=[],
            required=True,
        ),
        FieldSpec(
            namespace=ConfigNamespace.CHORE,
            key=ConfigKey.USE_FILE,
            value_type=bool,
            default=True,
        ),
        FieldSpec(
            namespace=ConfigNamespace.CHORE,
            key=ConfigKey.PERSONALITY,
            value_type=str,
            default=_PERSONALITY_DEFAULT,
        ),
    ),
)

_DATA_TAB = TabSpec(
    namespace=ConfigNamespace.DATA,
    fields=(
        FieldSpec(
            namespace=ConfigNamespace.DATA,
            key=ConfigKey.CLEARUP,
            value_type=float,
            default=6.0,
            bounds=(0.1, 720.0),
        ),
        FieldSpec(
            namespace=ConfigNamespace.DATA,
            key=ConfigKey.WAITING,
            value_type=float,
            default=0.5,
            bounds=(0.1, 720.0),
        ),
    ),
)

SHARED_TABS = (_GLOBAL_TAB, _AI_TAB, _CHORE_TAB, _DATA_TAB)
