"""实例插件状态读取

- 按状态文件路径读启用集与目录指纹两键
- 只取调用方点名的那一键
"""

from pathlib import Path

from .toml_read import read_toml


def load_instance_enabled(state_path: Path, enabled_key: str) -> frozenset[str] | None:
    """读取实例启用集

    - 读不到文件或解析失败时返回 None
    - 文件不存在即实例从未保存过插件选择
    - 名单成员按字符串收，非串成员取它的字面值
    """
    data = read_toml(state_path)
    if data is None:
        return None

    return frozenset(str(name) for name in data.get(enabled_key, []))


def load_instance_catalog(state_path: Path, catalog_key: str) -> str:
    """读取实例目录指纹

    - 缺失或损坏返回空串，与任何现算指纹都不等
    """
    data = read_toml(state_path)
    if data is None:
        return ""

    return str(data.get(catalog_key, ""))
