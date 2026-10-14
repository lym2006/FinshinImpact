# src/bootstrap/_plugin/__init__.py
"""插件面板域门面

- 代发插件面板入口与自动弹面板判定
"""

from ._maintain import open_maintain_menu
from ._manifest import panel_needed
from ._panel import MODE_AUTO, MODE_EDIT, open_panel
from ._startup import settle_runtime

__all__ = [
    # 面板入口
    "MODE_AUTO",
    "MODE_EDIT",
    "open_panel",
    # 启动裁决
    "panel_needed",
    "settle_runtime",
    # 环境维护
    "open_maintain_menu",
]
