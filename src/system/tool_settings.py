"""项目声明读取

- 配置表缺键即报错
- 插件目录那份声明只取依赖表，每次现读
"""

from pathlib import Path
from typing import Any

from .profile_env import DECLARATION_FILE_NAME, ROOT_DIR
from .toml_read import read_toml

# 两份声明的位置
_ROOT_DECLARATION = ROOT_DIR / DECLARATION_FILE_NAME
_DEVTOOLS_DIR = "devtools"
DEVTOOLS_DECLARATION = ROOT_DIR / _DEVTOOLS_DIR / DECLARATION_FILE_NAME

# 解析结果按路径缓存
_CACHE: dict[Path, dict[str, Any]] = {}


def declaration(path: Path = _ROOT_DECLARATION) -> dict[str, Any]:
    """取一份声明的解析结果

    - 读不出交出空表
    - 同一路径只读一次
    """
    if path not in _CACHE:
        _CACHE[path] = read_toml(path) or {}
    return _CACHE[path]


def project_value(key: str, path: Path = _ROOT_DECLARATION) -> str:
    """取声明项目段里的文本值

    - 缺键或非串交出空串
    """
    project = declaration(path).get("project")
    value = project.get(key) if isinstance(project, dict) else None
    return value if isinstance(value, str) else ""


def tool_setting(key: str) -> Any:
    """取根声明配置表里的键值

    - 表名即项目名，缺键即报错
    """
    tool = declaration().get("tool")
    table = tool.get(project_value("name")) if isinstance(tool, dict) else None
    if not isinstance(table, dict) or key not in table:
        raise RuntimeError(f"pyproject 缺 [tool.{project_value('name')}].{key}")
    return table[key]


def declared_dependencies(path: Path) -> tuple[str, ...] | None:
    """取一份声明的依赖表

    - 读不出或形状不合交出 None
    """
    data = read_toml(path)
    project = data.get("project") if data else None
    if not isinstance(project, dict):
        return None
    pins = project.get("dependencies", [])
    if not isinstance(pins, list) or not all(isinstance(pin, str) for pin in pins):
        return None

    return tuple(pins)
