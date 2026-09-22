# src/plugins/AI/state.py
"""并发状态（内部实现）

- 定义用户级并发锁与全局注册表
"""

from asyncio import Lock
from collections import defaultdict

# 用户级异步锁字典
# 当访问不存在的键（新用户）时，自动创建新的 asyncio.Lock 实例
user_locks: dict[str, Lock] = defaultdict(Lock)
