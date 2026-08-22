# src/plugins/AI/services/blacklist.py
"""
黑名单管理服务

负责：
- 黑名单文件的读取与保存
- 内存级缓存管理，防止高频 I/O
- 并发安全的状态维护
"""

import asyncio
import logging

from ..core.config import BLACK_DIR

logger = logging.getLogger("Bot.Plugins.AI.Auth")

# ==================== 常量配置 ====================
PATH = BLACK_DIR / "blacklist.txt"

# 内存缓存与并发锁（全进程共享）
_cache: list[str] | None = None
_lock = asyncio.Lock()


# ==================== 1. 黑名单读取 ====================
async def get_black_list() -> list[str]:
    """
    获取黑名单列表（优先读取内存缓存）

    首次调用时从磁盘加载并写入缓存，后续调用直接返回内存数据。
    使用 asyncio.Lock 确保高并发下不会触发多次磁盘读取。
    """
    global _cache

    # 1. 快速路径：如果缓存已存在，直接返回（无锁操作，性能极高）
    if _cache is not None:
        return _cache

    # 2. 慢速路径：缓存未命中，需要加锁读取磁盘
    async with _lock:
        # 双重检查：防止在等待锁的过程中，其他协程已经完成了加载
        if _cache is not None:
            return _cache

        if not PATH.exists():
            _cache = []
            return _cache

        try:
            # 使用 read_text 确保文件句柄在读取后自动关闭
            content = await asyncio.to_thread(PATH.read_text, encoding="utf-8")
            _cache = [line.strip() for line in content.splitlines() if line.strip()]
            logger.info(f"✅ 黑名单加载成功，共 {len(_cache)} 条记录")
        except Exception as e:
            logger.error(f"❌ 读取黑名单文件失败：{e}")
            _cache = []  # 读取失败时兜底为空列表，防止反复重试

        return _cache


# ==================== 2. 黑名单保存 ====================
async def save_black_list(black_list: list[str]) -> None:
    """保存黑名单列表到磁盘，并同步更新内存缓存"""
    global _cache

    # 加锁确保写入过程的原子性
    async with _lock:
        try:
            # 使用 write_text 确保文件句柄在写入后自动关闭
            content = "\n".join(black_list)
            await asyncio.to_thread(PATH.write_text, content, encoding="utf-8")

            # 写入成功后，立即同步更新内存缓存
            _cache = black_list
            logger.info(f"✅ 黑名单保存成功，当前共 {len(_cache)} 条记录")
        except Exception as e:
            logger.error(f"❌ 保存黑名单文件失败：{e}")
