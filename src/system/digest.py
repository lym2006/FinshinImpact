"""指纹计算

- 文件、字节、文本与行清单四种口径各一个出口
- 行清单按换行符连接后取指纹
"""

import hashlib
from collections.abc import Sequence
from pathlib import Path

# 行清单指纹的行连接符，改它等于换一份账
_LINES_JOIN = "\n"


def file_digest(path: Path) -> str:
    """算文件字节指纹

    - 读不出交出空串
    """
    try:
        return _bytes_digest(path.read_bytes())
    except OSError:
        return ""


def _bytes_digest(payload: bytes) -> str:
    """算一段字节的指纹"""
    return hashlib.sha256(payload).hexdigest()


def text_digest(text: str) -> str:
    """算一段文本的指纹"""
    return _bytes_digest(text.encode("utf-8"))


def lines_digest(lines: Sequence[str]) -> str:
    """算行清单的指纹

    - 行序参与取值
    """
    return text_digest(_LINES_JOIN.join(lines))
