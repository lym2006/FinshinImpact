# src/plugins/AI/services/_blacklist.py
"""黑名单服务（内部实现）

- 实现文件读写与内存缓存
- 提供并发安全的状态维护
"""

import asyncio

from utils import get_logger

from ..config import ai_config

logger = get_logger("Plg.AI.Auth")

# 内部常量配置
_PATH = ai_config.black_dir / "blacklist.txt"

# 内存缓存与并发锁（全进程共享）
_cache: list[str] | None = None
_lock = asyncio.Lock()

# ==================== 黑名单读取 ====================


async def get_black_list() -> list[str]:
    """获取黑名单（优先内存缓存）

    首次从磁盘加载，锁防并发重复读。
    """
    global _cache

    # 快速路径：如果缓存已存在，直接返回（无锁操作，性能极高）
    if _cache is not None:
        return _cache

    # 慢速路径：缓存未命中，需要加锁读取磁盘
    async with _lock:
        # 双重检查：防止在等待锁的过程中，其他协程已经完成了加载
        if _cache is not None:
            return _cache

        if not _PATH.exists():
            _cache = []
            return _cache

        try:
            # 使用 read_text 确保文件句柄在读取后自动关闭
            content = await asyncio.to_thread(_PATH.read_text, encoding="utf-8")
            _cache = [line.strip() for line in content.splitlines() if line.strip()]
            logger.info(f"黑名单加载成功，共 {len(_cache)} 条记录")
        except Exception as e:
            logger.send_error("读取黑名单文件失败", e)
            _cache = []  # 读取失败时兜底为空列表，防止反复重试

        return _cache


# ==================== 黑名单保存 ====================


async def save_black_list(black_list: list[str]) -> None:
    """保存黑名单

    落盘并同步更新内存缓存。
    """
    global _cache

    # 加锁确保写入过程的原子性
    async with _lock:
        try:
            # 使用 write_text 确保文件句柄在写入后自动关闭
            content = "\n".join(black_list)
            await asyncio.to_thread(_PATH.write_text, content, encoding="utf-8")

            # 写入成功后，立即同步更新内存缓存
            _cache = black_list
            logger.info(f"黑名单保存成功，当前共 {len(_cache)} 条记录")
        except Exception as e:
            logger.send_error("保存黑名单文件失败", e)
