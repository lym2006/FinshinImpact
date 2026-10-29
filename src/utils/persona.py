# src/utils/persona.py
"""人设正文组装

- 按实例副本、内置模板、空正文三级取正文并注入主人 id
- 生效正文与面板草稿各存一份，只在启动与落盘时按文件装填
- 运行期不读实例文件，取文件内容要走面板的重载按钮
- 重载按钮选完只落一条取用记录，覆盖文件与换生效正文都等保存那一步
- 取用记录同时留档两份正文，没保存就重启也拼得回当初的比对
- 组装规则单源，运行期与配置向导预览共用
"""

from dataclasses import dataclass
from enum import StrEnum

from system.profile_env import OWNER_PLACEHOLDER

from .logger import get_logger
from .paths import PERSONA_FILE, PERSONA_TEMPLATE

_logger = get_logger("Util.Persona")

# 生效正文与面板草稿三槽，生效正文只在启动与落盘两处按文件装填
_persona_text: str = ""  # 生效正文缓存，启动与落盘后按磁盘内容装填
_persona_prev: str = ""  # 草稿顶替前的生效正文，校验不过即从这份回退
_draft_text: str | None = None  # 面板草稿缓存，编辑窗确认与面板关闭时改写


@dataclass(frozen=True)
class _PersonaPending:
    """没保存成人设的那次取用

    - 只在本进程内比对，落盘与读取归 init_files
    """

    applied: str  # 拍板时的生效正文，文件里要被换成的那一份
    disk: str  # 拍板时的文件正文，草稿要被换成的那一份


# 待拍板槽：重载按钮记下两份正文，保存成功才抹掉这条记录
_pending: _PersonaPending | None = None


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


def read_persona_text() -> tuple[str, _PersonaSource]:
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


def applied_persona_text() -> str:
    """取当前生效正文

    - 只读缓存，实例文件只在装填那两处读
    """
    return _persona_text


def load_persona_cache() -> None:
    """按磁盘当前内容装填生效正文，并丢掉面板草稿

    - 只在启动与落盘两处调用，重载按钮选完不装填
    - 装填完磁盘与生效正文本就一致，待拍板记录随之撤掉
    - 退到模板或空正文时记错误，副本读不出只在这一处报
    """
    global _persona_text, _draft_text, _pending
    text, source = read_persona_text()
    if source != _PersonaSource.FILE:
        _logger.error(_FALLBACK_HINTS[source])
    _persona_text = text
    _draft_text = None
    _pending = None


def draft_persona_text() -> str:
    """取面板草稿正文

    - 未起稿即按生效正文，面板上屏的永远是同一份
    """
    return _draft_text if _draft_text is not None else _persona_text


def set_draft_persona(text: str) -> None:
    """把编辑窗确认过的正文写进草稿"""
    global _draft_text
    _draft_text = text


def clear_draft_persona() -> None:
    """丢掉草稿，面板取消时回到生效正文"""
    global _draft_text
    _draft_text = None


def mark_persona_pending(applied: str, disk: str) -> None:
    """记下两份正文不一致，等保存那一步再定谁覆盖谁

    - 只起内存记录，不动生效正文、不动草稿、不写文件
    """
    global _pending
    _pending = _PersonaPending(applied=applied, disk=disk)


def pending_persona() -> _PersonaPending | None:
    """交出待拍板记录，没记录即 None"""
    return _pending


def clear_persona_pending() -> None:
    """撤掉待拍板记录的内存那一份

    - 落盘与启动读档时用，文件那一份归 init_files 删
    """
    global _pending
    _pending = None


def apply_draft_persona() -> str | None:
    """生效缓存顶替成草稿正文并交出该正文

    - 只换缓存不写文件，校验不过由回退路径换回顶替前的正文
    - 草稿与生效正文一致即交空，这次没有人设变更
    """
    global _persona_text, _persona_prev
    draft = _draft_text
    if draft is None or draft == _persona_text:
        return None
    _persona_prev = _persona_text
    _persona_text = draft
    return draft


def revert_persona_cache() -> None:
    """生效缓存换回草稿顶替前的那份正文，草稿原样留着

    - 校验失败或取消回退时用，草稿待续存到下次保存
    """
    global _persona_text
    _persona_text = _persona_prev


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
