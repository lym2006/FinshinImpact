# src/plugins/AI/__init__.py
"""
AI 智能对话插件

导出：
- AI 核心对话与状态管理
- 渲染、截图与权限服务
"""

from .handlers import get_router

router = get_router()

__all__ = ["router"]
