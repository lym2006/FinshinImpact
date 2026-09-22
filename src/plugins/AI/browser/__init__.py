# src/plugins/AI/browser/__init__.py
"""浏览器单例句柄（内部实现）

- 提供 AI 全局浏览器共享入口
"""

from ._manager import browser_manager

__all__ = ["browser_manager"]
