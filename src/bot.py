# src/bot.py
"""
TelegramBot 主程序入口

负责：
- 初始化运行环境
- 加载配置与版本检查
- 注册中间件与路由
- 启动带有自动重连机制的异步轮询
"""

import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramNetworkError
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_exponential

from plugins.AI.services import cleanup_loop
from utils import (
    ConfigError,
    LoggingMiddleware,
    init_project_files,
    register_routers,
    setup_logger,
)
from utils.check_version import check_updates

# 初始化日志（必须最先执行，确保后续配置加载时可用）
logger = setup_logger()


# ==================== 1. 核心启动与重连逻辑 ====================
@retry(
    retry=retry_if_exception_type(TelegramNetworkError),
    stop=stop_after_delay(60),
    wait=wait_exponential(multiplier=1, max=10, min=1),
    before_sleep=lambda retry_state: logger.warning(
        f"🚨 机器人断开连接，准备第 {retry_state.attempt_number - 1} 次重连..."
    ),
    reraise=True,
)
async def start(dispatcher: Dispatcher, bot: Bot) -> None:
    """启动机器人并开始轮询，遇到网络异常时自动触发重连"""
    await dispatcher.start_polling(bot)


# ==================== 2. 主程序入口 ====================
async def main() -> None:
    """主程序入口，负责初始化环境、配置组件并启动机器人"""
    # 1. 基础环境初始化
    logger.info("🤖 TelegramBot 正在启动...")
    init_project_files()

    # 2. 加载配置与版本检查（必须在注册日志器之后导入）
    try:
        from utils import CONFIG, SafeSession

        proxy = CONFIG["network"]["proxy"]
        token = CONFIG["api_keys"]["telegram_token"]
    except ConfigError:
        sys.exit(1)

    if not await check_updates():
        sys.exit(1)

    # 3. 初始化核心组件
    session = SafeSession(proxy=proxy)
    bot = Bot(token=token, session=session)

    dispatcher = Dispatcher()
    dispatcher.update.outer_middleware(LoggingMiddleware())
    register_routers(dispatcher)

    # 4. 启动后台清理任务
    cleanup_task = asyncio.create_task(cleanup_loop())

    # 5. 启动机器人并处理异常
    logger.info("🎉 机器人连接成功，开始轮询更新...")
    try:
        await start(dispatcher, bot)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("👋 收到中断信号，正在安全关闭机器人...")
    except Exception as e:
        logger.error(f"❌ 发生未预期的错误: {e}")
    finally:
        # 安全取消后台清理任务
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

        # 关闭网络会话
        await bot.session.close()
        logger.info("💤 机器人已关闭")


# ==================== 3. 脚本直接运行入口 ====================
if __name__ == "__main__":
    asyncio.run(main())
