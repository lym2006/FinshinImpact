# src/plugins/AI_render/__init__.py
"""Markdown 渲染插件门面

- 加载时向 AI 注入渲染出口
- 导出 md 命令路由
"""

from ..AI.services.worker import set_render_provider
from ._handler import md_router as router
from ._services import render_html, screenshot

set_render_provider(render_html, screenshot)

__all__ = ["router"]
