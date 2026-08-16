import asyncio

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramNetworkError
from tenacity import retry, retry_if_exception_type, stop_after_delay, wait_exponential

from .plugins.AI.services import cleanup_loop
from .utils import AuthMiddleware, LoggingMiddleware, register_routers, setup_logger

logger = setup_logger()


@retry(
    retry=retry_if_exception_type(TelegramNetworkError),
    stop=stop_after_delay(60),
    wait=wait_exponential(multiplier=1, max=10, min=1),
    before=lambda retry_state: (
        logger.warning(
            f"🚨 机器人断开连接，准备第 {retry_state.attempt_number - 1} 次重连..."
        )
        if retry_state.attempt_number > 1
        else None
    ),
    reraise=True,
)
async def start(dp: Dispatcher, bot: Bot):
    await dp.start_polling(bot)


async def main():
    # 初始化日志
    logger.info("🤖 TelegramBot 正在启动...")

    # 导入配置
    from .utils import CONFIG, SafeSession

    # 初始化 Bot
    session = SafeSession(proxy=CONFIG["network"]["proxy"])
    bot = Bot(token=CONFIG["api_keys"]["telegram_token"], session=session)

    # 注册插件和中间件
    dp = Dispatcher()
    dp.update.outer_middleware(LoggingMiddleware())
    dp.update.outer_middleware(AuthMiddleware())
    register_routers(dp, CONFIG)

    # 启动后台清理任务
    asyncio.create_task(cleanup_loop())

    # ⚪️神启动！
    logger.info("🚀 机器人启动中...")
    try:
        logger.info("🎉 机器人连接成功，开始轮询更新...")
        await start(dp, bot)
    except KeyboardInterrupt:
        logger.info("👋 收到中断信号，正在关闭...")
    finally:
        await bot.session.close()
        logger.info("💤 机器人已关闭")


if __name__ == "__main__":
    asyncio.run(main())
