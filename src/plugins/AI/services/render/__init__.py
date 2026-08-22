# src/plugins/AI/services/render/__init__.py
"""
AI 视觉渲染组件

导出：
- HTML 渲染
- 页面截图与裁剪
"""

from .renderer import render_html
from .screenshot import screenshot

__all__ = [
    # HTML 渲染
    "render_html",
    # 页面截图与裁剪
    "screenshot",
]
