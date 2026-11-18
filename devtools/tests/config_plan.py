"""用例侧的配置段表装配

- 把配置文件指到临时目录，按本实例的来源清单装配一次
- 适配器入口件按给定的标题假造，用例不依赖挂载的适配器
"""

import shutil
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, patch

from bot._managers._config_sources import config_sources
from utils.config import ensure_config

_PARTS_TARGET = "bot._managers._config_sources.parts_for"


@contextmanager
def fake_adapter_parts(title: str = "Telegram") -> Iterator[None]:
    """把适配器入口件换成只交标题的那一份"""
    parts = Mock(spec=["title"], title=title)
    with patch(_PARTS_TARGET, return_value=parts):
        yield


def assemble_for_case(case: unittest.TestCase) -> Path:
    """装配一次段表，配置文件落临时目录

    - 段表随用例删掉，交回临时目录
    """
    root = Path(tempfile.mkdtemp())
    case.addCleanup(shutil.rmtree, root, True)
    with (
        patch("utils.config.CONFIG_FILE", root / "config.toml"),
        fake_adapter_parts(),
    ):
        ensure_config(config_sources())
    return root
