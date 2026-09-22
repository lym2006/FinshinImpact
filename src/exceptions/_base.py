# src/exceptions/_base.py
"""异常基类（内部实现）

- 定义 fatal 致命等级与标记机制
- 实现关键字参数存为属性供模板渲染
"""

from typing import Any, ClassVar


class BotError(Exception):
    """Bot 自定义异常基类"""

    fatal: ClassVar[bool] = False

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)
        super().__init__()
