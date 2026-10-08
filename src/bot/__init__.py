# src/bot/__init__.py
"""Bot 启动包

- 定义后台服务的模块边界
- 代发主程序装配入口 Main
"""

from ._main import Main

__all__ = ["Main"]
