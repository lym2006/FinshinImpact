# src/plugins/AI/core/_chat_context.py
"""会话上下文

- 收口在跑的摘要压缩协程，停服时统一取消
"""

import asyncio

# 跑完由 done_callback 自行摘除，不靠清理轮
active_tasks: set[asyncio.Task] = set()
