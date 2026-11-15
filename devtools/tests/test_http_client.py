"""HTTP 客户端建连的单元测试

- 建客户端不读环境里的代理表与绕过表
"""

import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from utils.network._client import BaseClient  # noqa: E402

# 绕过表里的 IPv6 写法是这条用例的触发条件，删掉即测不到东西
_ENV_PROXY = {"NO_PROXY": "localhost,[::1],::1", "HTTPS_PROXY": "http://127.0.0.1:8"}


class ProxySourceCase(unittest.TestCase):
    """代理只由参数注入"""

    def test_client_builds_without_reading_env(self) -> None:
        """环境里的代理表再怪也建得起客户端

        - 这条红了说明建客户端又去读环境了
        """

        async def build() -> None:
            async with BaseClient._create_client(base_url="https://example.invalid"):
                pass

        with patch.dict(os.environ, _ENV_PROXY, clear=False):
            asyncio.run(build())


if __name__ == "__main__":
    unittest.main()
