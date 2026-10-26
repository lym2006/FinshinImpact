# src/plugins/grant/__init__.py
"""授权插件门面

- /grant 与 /ungrant：管理命令的授权名单
"""

from ._commands import router

__all__ = ["router"]
