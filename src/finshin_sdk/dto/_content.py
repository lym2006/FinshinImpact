# src/finshin_sdk/dto/_content.py
"""内容数据传输对象

- 定义消息内容和媒体索引
"""

from dataclasses import dataclass

from ..domain import ContentKind
from ..domain.ids import MessageId


@dataclass(frozen=True, slots=True)
class ContentDTO:
    """消息内容

    - 平台负载归一
    """

    text: str = ""  # 文字正文，媒体消息是种类标记加附文，无附文即空
    file_name: str = ""
    media: tuple["MediaEntryDTO", ...] = ()


@dataclass(frozen=True, slots=True)
class MediaEntryDTO:
    """媒体索引条目

    - 与 media_asset 表对应
    - 相册按张给 id 与附文，单条消息只有一项
    """

    kind: ContentKind
    local_path: str
    slot: int = 0  # 同消息内多个媒体的序号
    size_bytes: int = 0
    message_id: MessageId = MessageId("")  # 该张所在消息 id，外发定位用
    caption: str = ""  # 该张自带附文
