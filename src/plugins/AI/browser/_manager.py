# src/plugins/AI/browser/_manager.py
"""浏览器生命周期（内部实现）

- 实现懒加载单例与安全关闭
"""

import asyncio

from playwright.async_api import Browser, Playwright, async_playwright

from utils import get_logger, register_lifecycle

from ._config import browser_config

logger = get_logger("Plg.AI.Browser")


class BrowserManager:
    """全局浏览器生命周期管家"""

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._lock = asyncio.Lock()  # 防止并发下启动多个浏览器

    async def get_browser(self) -> Browser:
        """获取全局浏览器实例"""
        # 未启动或已断开则自动初始化（懒加载 + 双重检查锁）
        # 无锁，高性能
        if self._browser and self._browser.is_connected():
            return self._browser

        # 加锁，防并发
        async with self._lock:
            if self._browser and self._browser.is_connected():
                return self._browser

            # 注册关闭钩子
            register_lifecycle(self._shutdown, "Playwright 浏览器", "hook_async")

            logger.info("正在初始化全局 Playwright 浏览器...")
            # 启动 Playwright 引擎
            self._playwright = await async_playwright().start()
            # 启动 Chromium 浏览器
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=browser_config.args,
            )
            logger.info("全局浏览器初始化成功")
            return self._browser

    async def _shutdown(self) -> None:
        """关闭浏览器与引擎"""
        async with self._lock:
            if self._browser:
                logger.info("正在关闭全局浏览器...")
                try:
                    await self._browser.close()
                except Exception as e:
                    logger.send_error("关闭浏览器错误", e)
                finally:
                    self._browser = None

            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception as e:
                    logger.send_error("停止 Playwright 引擎失败", e)
                finally:
                    self._playwright = None

            logger.info("全局浏览器资源已彻底释放")


# 极其冷酷的全局单例（整个 AI 插件共享这一个管家）
browser_manager = BrowserManager()
