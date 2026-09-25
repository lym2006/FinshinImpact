# src/utils/plugins_register.py
"""插件注册表（内部实现）

- 实现白名单加载顺序控制
- 实现路由注册与逐项结果上报
- 纯工具层：零日志，加载结果以报告列表返回上层记录
"""

import importlib

from aiogram import Dispatcher

from exceptions import PluginsMissingError

# 加载白名单：顺序即优先级，欢迎帮助在前、核心 AI 必须最后
_PLUGIN_ORDER = [
    "welcome",  # 系统级命令
    "help",  # 帮助命令

    # "spider",  #爬虫相关
    # "image_record",  #图像音频相关
    # "emoji",  #emoji合成
    "AI",  # AI部分
]

# 逐项报告：(插件名, 是否成功, 失败原因)
_PluginReport = list[tuple[str, bool, str]]


def register_routers(dispatcher: Dispatcher) -> _PluginReport:
    """按顺序注册插件

    返回逐项报告；全部失败抛 PluginsMissingError。
    """
    report: _PluginReport = []
    success_count = 0

    for plugin_name in _PLUGIN_ORDER:
        try:
            # 动态导入插件模块
            module = importlib.import_module(f"plugins.{plugin_name}")

            # 检查插件是否导出了标准的 router 对象
            router = getattr(module, "router", None)
            if router is None:
                report.append(
                    (
                        plugin_name,
                        False,
                        "缺少 router 属性（检查 __init__.py 是否导出 router）",
                    )
                )
                continue

            # 清除旧的父路由引用，允许重新附加到新 Dispatcher
            router._parent_router = None
            dispatcher.include_router(router)
            report.append((plugin_name, True, ""))
            success_count += 1

        except ModuleNotFoundError as e:
            if f"plugins.{plugin_name}" in str(e):
                reason = "未找到（检查目录结构）"  # 插件本身不存在
            else:
                # 插件内部缺少依赖
                reason = f"内部依赖缺失: {e}"
            report.append((plugin_name, False, reason))

        except Exception as e:
            report.append((plugin_name, False, f"{type(e).__name__}: {e}"))

    # 如果所有插件都加载失败，抛出异常
    if success_count == 0:
        raise PluginsMissingError() from None

    return report
