# src/plugins/AI/__init__.py
"""AI 插件门面

- 提供对话与记忆命令入口
- 声明随 Bot 起停的过期记录清理协程
"""

from .handlers import get_router
from .services import cleanup_loop

# 插件契约
router = get_router()
backgrounds = (cleanup_loop,)

__all__ = [
    # 插件契约
    "router",
    "backgrounds",
]
