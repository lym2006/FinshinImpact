import asyncio
import logging
import numpy as np
from pathlib import Path
from PIL import Image
from playwright.async_api import async_playwright,Error as PlaywrightError

from ...config import cupa

logger=logging.getLogger("Bot.Plugins.AI.Render")
_semaphore=asyncio.Semaphore(3)

async def screenshot(nm:str,path:str) -> str|None:
    async with _semaphore:
        try:
            pa=await _get_screenshot(nm,path)
            if pa:
                await asyncio.to_thread(_crop_screenshot,pa)
            return pa
        except Exception as e:
            logger.error(f"❌ 截图任务整体失败: {e}")
            return None

async def _get_screenshot(nm:str,path:str) -> str|None:
    if not Path(path).exists():
        logger.error(f"❌ 源文件不存在: {path}")
        return None
    pa=str(cupa/f"{nm}.png")
    browser=None
    try:
        async with async_playwright() as p:
            browser=await p.chromium.launch(
                headless=True,
                args=[
                    '--disable-gpu',                     # 禁用GPU硬件加速，无头服务器无显卡驱动，防黑屏崩溃
                    '--no-sandbox',                      # 关闭沙箱隔离，Linux/Docker环境下Chrome默认权限不足无法启动沙箱
                    '--force-device-scale-factor=2',     # 200% 像素密度，保证截图清晰
                    '--high-dpi-support=2',              # 配合上面的高 DPI 支持
                    '--disable-font-antialiasing',       # 关闭字体抗锯齿，减少边框颜色渲染偏差
                    '--disable-partial-raster',          # 禁用部分光栅化，减少渲染管线干预
                    '--ignore-certificate-errors',       # 忽略SSL证书错误，file:///协议加载本地资源用
                    '--allow-insecure-localhost',        # 允许localhost访问不安全内容
                    '--disable-dev-shm-usage'            # 服务器/Docker 环境防崩溃
                ]
            )
            page=await browser.new_page()
            await page.goto(f'file:///{path}',wait_until='networkidle',timeout=30000)
            await page.wait_for_timeout(2000)
            dimensions=await page.evaluate("""() => {
                return {
                    width:document.body.scrollWidth,
                    height:document.body.scrollHeight
                }
            }""")
            new_width=max(int(dimensions['width'])+100,800)
            new_height=max(int(dimensions['height'])+100,10000)
            await page.set_viewport_size({"width":new_width,"height":new_height})
            await page.wait_for_timeout(1000)
            await page.screenshot(path=pa,full_page=False)
            logger.info(f"✅ 截图已保存: {pa}")
    except PlaywrightError as e:
        logger.error(f"❌ PlayWright引擎错误: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ 截图发生未知错误: {e}")
        return None
    finally:
        if browser:
            try:
                await browser.close()
            except:
                pass
    return pa

def _crop_screenshot(pa:str):
    try:
        img=Image.open(pa).convert('RGB')
        img_array=np.array(img)
        if img_array.size==0:
            logger.warning(f"⚠️ 图片内容为空，跳过裁剪: {pa}")
            return
        ORANGE=np.array([255,165,0])
        is_orange=np.all(img_array==ORANGE,axis=-1)
        rows=np.where(~np.all(is_orange,axis=1))[0]
        cols=np.where(~np.all(is_orange,axis=0))[0]
        if rows.size==0 or cols.size==0:
            logger.warning("⚠️ 未检测到有效内容，保留原图")
            return
        top,bottom=rows[0],rows[-1]+1
        left,right=cols[0],cols[-1]+1
        cropped_array=img_array[top:bottom, left:right]
        cropped_img=Image.fromarray(cropped_array)
        cropped_img.save(pa)
        logger.info(f"✅ 裁剪成功！\n原尺寸: {img.size}\n新尺寸: {cropped_img.size}\n区域: ({left}, {top}) 到 ({right}, {bottom})")
    except Exception as e:
        logger.error(f"❌ 裁剪出错: {e}")