# src/messages/__init__.py
"""文案中心

- 用户可见文案单源，按域拆小文件，每条标注使用位置
- 每个域打包为一个 XXXMessage 类，禁止散装字符串导出
- 异常模板留在 exceptions 映射表，theme 令牌仅代理引用
- 启动器 exe 无法 import 本包，其弹窗文案独立自持
"""

from ._check import CheckMessage
from ._dialog import DialogMessage
from ._misc import MiscMessage
from ._picker import PickerMessage
from ._version import VersionMessage

__all__ = [
    # 引导期选窗
    "PickerMessage",
    # 主窗与专属弹窗
    "MiscMessage",
    "DialogMessage",
    # 网络检查与更新
    "CheckMessage",
    "VersionMessage",
]
