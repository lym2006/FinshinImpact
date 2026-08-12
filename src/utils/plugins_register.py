import importlib
import logging
from typing import Dict,Any
from aiogram import Dispatcher

logger=logging.getLogger("Bot.Plugins.Setup")
PLUGIN_ORDER = [# welcome 和 help 一定要在第一、二个，AI 一定要在最后一个，不建议调整注册顺序
    "welcome",          #系统级命令
    "help",             #帮助命令
    #"spider",          #爬虫相关
    #"image_record",    #图像音频相关
    #"emoji",           #emoji合成
    "AI"                #AI部分
]

def register_routers(dp:Dispatcher,CONFIG:Dict[str,Any]):
    logger.info(f"🔌 开始加载 {len(PLUGIN_ORDER)} 个插件...")
    success_count=0
    for index,plugin_name in enumerate(PLUGIN_ORDER,start=1):
        try:
            module=importlib.import_module(f"src.plugins.{plugin_name}")
            if hasattr(module,"router"):
                dp.include_router(module.router)
                logger.info(f"✅ [{index}/{len(PLUGIN_ORDER)}] 插件 {plugin_name} 注册成功")
                success_count+=1
            else:
                logger.error(f"❌ [{index}] 插件 '{plugin_name}' 缺少 'router' 属性 (请检查 __init__.py)")
        except ModuleNotFoundError:
            logger.error(f"❌ [{index}] 插件 '{plugin_name}' 未找到 (检查文件名/文件夹名)")
        except Exception as e:
            logger.error(f"❌ [{index}] 插件 '{plugin_name}' 加载异常: {e}",exc_info=True)
    logger.info(f"🎉 插件加载完成 | 成功: {success_count} / 总计: {len(PLUGIN_ORDER)}")
    if success_count==0:
        logger.critical("⚠️ 警告：未加载任何插件！")