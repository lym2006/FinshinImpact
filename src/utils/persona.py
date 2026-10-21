# src/utils/persona.py
"""人设正文组装

- 按实例副本、内置模板、空正文三级取正文并注入主人 id
- 组装规则单源，运行期与配置向导预览共用
"""

from enum import StrEnum

from system.profile_env import OWNER_PLACEHOLDER

from .logger import get_logger
from .paths import PERSONALITY_EXAMPLE, PERSONALITY_FILE

_persona_text: str | None = None  # 生效正文缓存，保存、覆盖与启动时重新装填

_logger = get_logger("Util.Persona")


class PersonaSource(StrEnum):
    """人设正文来源

    - 预览弹窗的来源提示与回退判定共用，禁裸写协议串
    """

    FILE = "file"
    TEMPLATE = "template"
    EMPTY = "empty"


# 退到内置模板或空正文时的日志句，副本每轮都读不出会刷同一条
_FALLBACK_HINTS = {
    PersonaSource.TEMPLATE: "实例人设副本读不出，本轮正文退回内置默认模板",
    PersonaSource.EMPTY: "实例人设副本与内置模板均读不出，正文为空",
}


def read_persona_text() -> tuple[str, PersonaSource]:
    """读磁盘当前正文

    - 副本读不出退内置模板，模板也读不出退空正文
    - 只读不装填缓存，预览与判定拿到的即磁盘真值
    """
    for path, source in (
        (PERSONALITY_FILE, PersonaSource.FILE),
        (PERSONALITY_EXAMPLE, PersonaSource.TEMPLATE),
    ):
        try:
            return path.read_text(encoding="utf-8"), source
        except OSError:
            continue
    return "", PersonaSource.EMPTY


def applied_persona_text() -> str:
    """取当前生效正文

    - 缓存未装填即按磁盘当前正文，两者此时本就一致
    """
    return _persona_text if _persona_text is not None else read_persona_text()[0]


def reset_persona_cache() -> None:
    """重置人设正文缓存

    - 实例人设文件被换掉后调用，下一轮组装重新读文件
    """
    global _persona_text
    _persona_text = None


def reload_persona_cache() -> bool:
    """把生效正文缓存换成磁盘当前内容

    - 缓存未装填不作判定，组装自然按磁盘内容填
    - 返回正文是否发生变化
    """
    global _persona_text
    if _persona_text is None:
        return False
    current = read_persona_text()[0]
    if current == _persona_text:
        return False
    _persona_text = current
    return True


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
    return inject_owner(_read_cached(), owner_id)


def _read_cached() -> str:
    """取缓存正文，未装填即按磁盘三级读一次

    - 退到模板或空正文时记错误，副本每轮都读不出会刷同一条
    """
    global _persona_text
    if _persona_text is None:
        text, source = read_persona_text()
        if source is not PersonaSource.FILE:
            _logger.error(_FALLBACK_HINTS[source])
        _persona_text = text
    return _persona_text
