# src/messages/__init__.py
"""文案中心

- 用户可见文案按域拆小文件，每条标注使用位置
- 每个域打包为一个 XXXMessage 类
- 异常模板留在 exceptions 映射表，theme 令牌代理引用
"""

from ._check import CheckMessage
from ._dialog import DialogMessage
from ._engine import EngineMessage
from ._misc import MiscMessage
from ._picker import PickerMessage
from ._plugin import PluginMessage
from ._version import VersionMessage

__all__ = [
    # 引导期选窗
    "PickerMessage",
    "PluginMessage",
    # 主窗与专属弹窗
    "MiscMessage",
    "DialogMessage",
    # 网络检查与更新
    "CheckMessage",
    "VersionMessage",
    # 引擎与链路
    "EngineMessage",
]
