# src/plugins/AI/services/render/screenshot.py
"""
页面截图与智能裁剪服务

负责：
- Playwright 无头浏览器懒加载与并发控制
- 网页 HTML 转高清 PNG 截图
- 基于像素颜色的智能边框裁剪
"""

import asyncio
import logging
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.async_api import Browser, async_playwright
from playwright.async_api import Error as PlaywrightError

from ...core.config import RECORD_DIR

logger = logging.getLogger("Bot.Plugins.AI.Render")

# ==================== 常量配置 ====================
# 浏览器并发控制：最多允许同时执行的截图任务数
MAX_CONCURRENT_SCREENSHOTS = 3

# Playwright 超时与等待时间（毫秒）
PAGE_LOAD_TIMEOUT = 30000
WAIT_AFTER_LOAD = 2000
WAIT_AFTER_RESIZE = 1000

# 视口尺寸配置
VIEWPORT_SAFE_MARGIN = 100  # 视口安全边距，防止内容贴边被裁切
MIN_VIEWPORT_WIDTH = 800  # 最小视口宽度
RENDER_CANVAS_HEIGHT = 10000  # 渲染画布高度（撑大视口，确保完整渲染，后续裁剪）

# 智能裁剪颜色：检测 HTML 中定义的橙色背景边框 (#FFA500)
ORANGE = np.array([255, 165, 0])

# PlayWright
ARGS = [
    "--disable-gpu",  # 禁用GPU硬件加速，无头服务器无显卡驱动，防黑屏崩溃
    "--no-sandbox",  # 关闭沙箱隔离，Linux/Docker环境下Chrome默认权限不足无法启动沙箱
    "--force-device-scale-factor=2",  # 200% 像素密度，保证截图清晰
    "--high-dpi-support=2",  # 配合上面的高 DPI 支持
    "--disable-font-antialiasing",  # 关闭字体抗锯齿，减少边框颜色渲染偏差
    "--disable-partial-raster",  # 禁用部分光栅化，减少渲染管线干预
    "--ignore-certificate-errors",  # 忽略SSL证书错误，file:///协议加载本地资源用
    "--allow-insecure-localhost",  # 允许localhost访问不安全内容
    "--disable-dev-shm-usage",  # 服务器/Docker 环境防崩溃
]

# ==================== 1. 全局状态与浏览器管理 ====================
_semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCREENSHOTS)
_browser: Browser | None = None


async def _get_browser() -> Browser:
    """懒加载全局浏览器实例，避免每次截图都重启浏览器"""
    global _browser
    if _browser is None or not _browser.is_connected():
        logger.info("🚀 正在初始化全局浏览器...")
        p = await async_playwright().start()
        _browser = await p.chromium.launch(
            headless=True,
            args=ARGS,
        )
    return _browser


# ==================== 2. 底层截图逻辑 ====================
async def _get_screenshot(file_name: str, html_path: str) -> str | None:
    """执行截图逻辑

    Args:
        file_name: 截图保存文件名（不含后缀）
        html_path: 原始 HTML 文件路径

    Returns:
        截图保存路径，若失败则返回 None
    """
    if not Path(html_path).exists():
        logger.error(f"❌ 源文件不存在: {html_path}")
        return None

    new_path = str(RECORD_DIR / f"temp/{file_name}.png")
    page = None
    try:
        browser = await _get_browser()
        page = await browser.new_page()

        await page.goto(
            f"file:///{html_path}",
            wait_until="networkidle",
            timeout=PAGE_LOAD_TIMEOUT,
        )
        await page.wait_for_timeout(WAIT_AFTER_LOAD)

        dimensions = await page.evaluate("""() => {
            return {
                width:document.body.scrollWidth,
                height:document.body.scrollHeight
            }
        }""")

        new_width = max(
            int(dimensions["width"]) + VIEWPORT_SAFE_MARGIN, MIN_VIEWPORT_WIDTH
        )
        new_height = max(
            int(dimensions["height"]) + VIEWPORT_SAFE_MARGIN, RENDER_CANVAS_HEIGHT
        )

        await page.set_viewport_size({"width": new_width, "height": new_height})
        await page.wait_for_timeout(WAIT_AFTER_RESIZE)
        await page.screenshot(path=new_path, full_page=False)
        logger.info(f"✅ 截图已保存: {new_path}")

    except PlaywrightError as e:
        logger.error(f"❌ PlayWright引擎错误: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ 截图发生未知错误: {e}")
        return None
    finally:
        # 关闭 Page，防止内存泄漏
        if page:
            try:
                await page.close()
            except Exception:
                pass
    return new_path


# ==================== 3. 智能裁剪逻辑 ====================
def _crop_screenshot(file_path: str) -> None:
    """基于像素颜色智能裁剪截图（同步函数，需在线程池中运行）

    Args:
        file_path: 截图保存文件路径
    """
    try:
        img = Image.open(file_path).convert("RGB")
        img_array = np.array(img)

        if img_array.size == 0:
            logger.warning(f"🚨 图片内容为空，跳过裁剪: {file_path}")
            return

        is_orange = np.all(img_array == ORANGE, axis=-1)
        rows = np.where(~np.all(is_orange, axis=1))[0]
        cols = np.where(~np.all(is_orange, axis=0))[0]

        if rows.size == 0 or cols.size == 0:
            logger.warning("🚨 未检测到有效内容，保留原图")
            return

        top, bottom = rows[0], rows[-1] + 1
        left, right = cols[0], cols[-1] + 1

        cropped_array = img_array[top:bottom, left:right]
        cropped_img = Image.fromarray(cropped_array)
        cropped_img.save(file_path)

        logger.info(
            f"✅ 裁剪成功！\n原尺寸: {img.size}\n新尺寸: {cropped_img.size}\n区域: ({left}, {top}) 到 ({right}, {bottom})"
        )
    except (OSError, ValueError) as e:
        logger.error(f"❌ 裁剪出错: {e}")


# ==================== 4. 截图主入口 ====================
async def screenshot(file_name: str, html_path: str) -> str | None:
    """截图主入口，带并发控制与异常兜底

    Args:
        file_name: 截图保存文件名（不含后缀）
        html_path: 原始 HTML 文件路径

    Returns:
        裁剪后的截图保存路径，若失败则返回 None
    """
    async with _semaphore:
        try:
            new_path = await _get_screenshot(file_name, html_path)
            if new_path:
                # 将同步的 CPU 密集型裁剪任务放入线程池，避免阻塞事件循环
                await asyncio.to_thread(_crop_screenshot, new_path)
            return new_path
        except Exception as e:
            logger.error(f"❌ 截图任务整体失败: {e}")
            return None
