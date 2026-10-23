# src/utils/plugin/__init__.py
"""插件工具门面

- 代发清单读取与注册表的多消费方符号
- 包名单数，与顶层复数容器 src/plugins 区分
"""

from ._manifest import enabled_manifests
from ._register import register_plugins

__all__ = [
    # 清单消费
    "enabled_manifests",
    # 插件注册
    "register_plugins",
]
