# src/core/dto/_content.py
"""内容数据传输对象

- 定义消息内容和媒体索引
"""

from dataclasses import dataclass

from ..domain import ContentKind
from ._identity import MsgReferenceDTO


@dataclass(frozen=True, slots=True)
class ContentDTO:
    """消息内容

    - 平台负载归一
    """

    text: str = ""  # 文本消息或媒体描述
    file_name: str = ""
    file_token: str = ""  # 平台侧文件标识，惰性下载
    origin_ref: MsgReferenceDTO | None = None  # 媒体所在消息，引用或附带媒体时非空
    media: tuple["MediaEntryDTO", ...] = ()


@dataclass(frozen=True, slots=True)
class MediaEntryDTO:
    """媒体索引条目

    - 与 media_asset 表对应
    """

    kind: ContentKind
    local_path: str
    slot: int = 0  # 同消息内多个媒体的序号
    size_bytes: int = 0
