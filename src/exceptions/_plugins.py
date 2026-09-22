# src/exceptions/_plugins.py
"""插件异常族（内部实现）

- 定义插件注册与生命周期异常
"""

from ._base import BotError

# ==================== 总插件异常 ====================


class PluginsError(BotError):
    """插件异常基类"""


class PluginsMissingError(PluginsError):
    """未注册插件"""

    fatal = True  # 环境缺失非配置可修，向导无从补救


# ==================== AI 插件异常 ====================


class AIError(PluginsError):
    """AI 插件异常基类"""


class AITaskStoppedError(AIError):
    """AI 任务中断异常"""
