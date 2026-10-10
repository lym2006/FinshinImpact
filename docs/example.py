# docs/example.py
"""代码格式规范模板

- 示范合规文件的骨架排列与注释排版
- 分区靠自上而下的顺序表达，不写区块标题
"""

import asyncio

from utils import get_logger

logger = get_logger("Example")  # 日志器名自动加 Bot. 前缀
_MAX_RETRIES = 3  # 网络重试上限


async def fetch_profile() -> None:
    """拉取实例配置

    - 标题行写简单动作，一行说得完就不开详情段
    - 详情段一行一个要点，一律 - 起头
    """
    # 实现细节的为什么写在函数体内，不进 docstring


async def main() -> None:
    """串起启动流程"""
    await fetch_profile()


if __name__ == "__main__":
    asyncio.run(main())
