# src/plugins/AI/services/_render/__init__.py
"""渲染服务门面（内部实现）

- 提供 HTML 渲染与截图出口
"""

from ._renderer import render_html
from ._screenshot import screenshot

__all__ = [
    # HTML 渲染
    "render_html",
    # 页面截图与裁剪
    "screenshot",
]
