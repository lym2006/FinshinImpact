# src/plugins/AI_render/browser/__init__.py
"""浏览器单例句柄

- 提供渲染插件全局浏览器入口
"""

from ._manager import browser_manager

__all__ = ["browser_manager"]
