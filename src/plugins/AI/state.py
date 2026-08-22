# src/plugins/AI/state.py
"""
AI 模块全局状态管理

集中存放跨请求共享的状态数据

提供：
- 用户级并发控制锁
"""

from asyncio import Lock
from collections import defaultdict

# 用户级异步锁字典
# 当访问不存在的键（新用户）时，自动创建新的 asyncio.Lock 实例
user_locks: dict[str, Lock] = defaultdict(Lock)
