# src/utils/persona.py
"""人设正文组装

- 读取实例人设文件并注入主人占位符
- 组装规则单源，运行期与配置向导预览共用
"""

from enum import Enum

from profile_env import OWNER_PLACEHOLDER

from .init_files import PERSONALITY_FILE

_persona_text: str | None = None  # 实例人设进程内不变，读一次即缓存


class PersonaSource(Enum):
    """人设正文来源

    - 预览弹窗的来源提示与回退判定共用，禁裸写协议串
    """

    FILE = "file"
    CONFIG = "config"
    MISSING = "missing"


def _read_file() -> str | None:
    """读实例人设文件

    - 缺失或读取失败返回 None，由调用方回退配置里的字符串
    """
    global _persona_text
    if _persona_text is None:
        try:
            _persona_text = PERSONALITY_FILE.read_text(encoding="utf-8")
        except OSError:
            return None
    return _persona_text


def persona_source(use_file: bool) -> PersonaSource:
    """当前勾选态下的正文来源"""
    if not use_file:
        return PersonaSource.CONFIG
    return PersonaSource.FILE if _read_file() is not None else PersonaSource.MISSING


def _inject_owner(text: str, owner_id: str) -> str:
    """注入主人 id

    - 主人 id 留空时不替换占位符
    - 人设中不存在占位符时原样返回
    """
    if not owner_id.strip():
        return text
    return text.replace(OWNER_PLACEHOLDER, owner_id)


def build_persona(fallback: str, use_file: bool, owner_id: str) -> str:
    """组装人设正文

    - 勾选 use_file 则优先读实例人设文件，读不到回退配置字符串
    - 占位符替换后逐字节稳定，禁在其中拼时间戳等每轮变化的内容
    """
    text = _read_file() if use_file else None
    return _inject_owner(text if text is not None else fallback, owner_id)
