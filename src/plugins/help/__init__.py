# src/plugins/help/__init__.py
"""帮助插件门面

- /help：帮助命令路由出口
"""

from ._commands import spec
from ._services import prewarm

prewarm()  # 引擎启动前重画一次帮助图

__all__ = ["spec"]
