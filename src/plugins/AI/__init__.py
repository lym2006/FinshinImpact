# src/plugins/AI/__init__.py
"""AI 插件门面

- 提供对话、渲染与权限服务出口
"""

from .handlers import get_router

router = get_router()
__all__ = ["router"]
