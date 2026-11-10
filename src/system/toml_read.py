# src/system/toml_read.py
"""TOML 文件读取

- 读不出即返回空值，缺与坏由调用方各自判
"""

import tomllib
from pathlib import Path
from typing import Any


def read_toml(path: Path) -> dict[str, Any] | None:
    """读取一份 TOML 文件

    - 不是文件、读不出或语法坏返回 None
    """
    if not path.is_file():
        return None
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
