# src/utils/persona.py
"""人设正文组装

- 按上次生效存档、实例副本、内置模板、空正文四级取正文并注入主人 id
- 生效正文一槽，启动与落盘后按存档装填
- 运行期不读实例文件，取文件内容要走面板的重载按钮
- 组装规则单源，运行期与配置向导预览共用
"""

from enum import StrEnum

from system.atomic_write import write_bytes_atomic
from system.profile_env import OWNER_PLACEHOLDER

from .logger import get_logger
from .paths import PERSONA_APPLIED, PERSONA_FILE, PERSONA_TEMPLATE

_logger = get_logger("Util.Persona")

# 生效正文一槽，按上次生效存档装填
_persona_text: str = ""


class _PersonaSource(StrEnum):
    """人设正文来源

    - 只用于装填时的回退判定，禁裸写协议串
    """

    FILE = "file"
    TEMPLATE = "template"
    EMPTY = "empty"


# 退到内置模板或空正文时的日志句，副本读不出只在装填那一处报
_FALLBACK_HINTS = {
    _PersonaSource.TEMPLATE: "实例人设副本读不出，正文退回内置默认模板",
    _PersonaSource.EMPTY: "实例人设副本与内置模板均读不出，正文为空",
}


def _read_persona_text() -> tuple[str, _PersonaSource]:
    """读磁盘当前正文

    - 副本读不出退内置模板，模板也读不出退空正文
    - 只读不装填缓存，预览与判定拿到的即磁盘真值
    """
    for path, source in (
        (PERSONA_FILE, _PersonaSource.FILE),
        (PERSONA_TEMPLATE, _PersonaSource.TEMPLATE),
    ):
        try:
            return path.read_text(encoding="utf-8"), source
        except OSError:
            continue
    return "", _PersonaSource.EMPTY


def read_template_text() -> str:
    """读内置默认模板正文

    - 读不出返回空串，是否停手由调用方判
    """
    try:
        return PERSONA_TEMPLATE.read_text(encoding="utf-8")
    except OSError:
        return ""


def read_persona_file() -> str | None:
    """读实例人设副本

    - 读不出交 None，不拿模板顶替
    """
    try:
        return PERSONA_FILE.read_text(encoding="utf-8")
    except OSError:
        return None


def applied_persona_text() -> str:
    """取当前生效正文

    - 只读缓存，存档与实例文件只在装填那两处读
    """
    return _persona_text


def save_applied_persona(text: str) -> bool:
    """把正文落成上次生效存档

    - 存原文正文，主人占位符保持字面，换主人不被判成正文变了
    - 写不进返回 False，存档保持原样
    """
    try:
        write_bytes_atomic(PERSONA_APPLIED, text.encode("utf-8"))
    except OSError:
        return False
    return True


def load_persona_cache() -> None:
    """按上次生效存档装填生效正文

    - 存档缺失即以文件正文补落一次，新实例自此有了比对基准
    - 退到模板或空正文时记错误，副本读不出只在装填那一处报
    """
    global _persona_text
    try:
        _persona_text = PERSONA_APPLIED.read_text(encoding="utf-8")
        return
    except OSError:
        _logger.debug("人设生效存档缺失，按实例文件补落")
    text, source = _read_persona_text()
    if source != _PersonaSource.FILE:
        _logger.error(_FALLBACK_HINTS[source])
    _persona_text = text
    if source == _PersonaSource.FILE:
        save_applied_persona(text)


def inject_owner(text: str, owner_id: str) -> str:
    """注入主人 id

    - 主人 id 留空时不替换占位符
    - 人设中不存在占位符时原样返回
    """
    if not owner_id.strip():
        return text
    return text.replace(OWNER_PLACEHOLDER, owner_id)


def build_persona(owner_id: str) -> str:
    """组装生效正文

    - 正文取缓存，主人 id 每次注入
    - 占位符替换后逐字节稳定，禁在其中拼时间戳等每轮变化的内容
    """
    return inject_owner(_persona_text, owner_id)
