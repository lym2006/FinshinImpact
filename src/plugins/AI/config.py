# plugins/AI/config.py
"""AI 配置（内部实现）

- 提供静态默认值与动态配置入口
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bot.error_guard import error_guard
from utils import BLACKLIST_DIR, RECORDS_DIR, config_manager

from .utils import build_message


# 静态配置：所有不变的东西都放在这里
@dataclass(frozen=True)
class _StaticAIConfig:
    """静态配置

    存放固定不变的值。
    """

    record_dir: Path = RECORDS_DIR  # 路径配置
    black_dir: Path = BLACKLIST_DIR

    # API 与模型基础配置
    base_url: str = "https://api.siliconflow.cn/v1"
    request_path: str = "/chat/completions"
    msg_chunk_size: int = 4000  # 消息发送相关
    flood_threshold: int = 5
    think_throttle_sec: float = 1.2
    trim_preview_len: int = 2000


_HOUR_SECONDS = 60 * 60


# 动态代理：负责实时获取变化的值
class _DynamicAIConfig:
    """动态配置代理

    属性访问实时透传配置中心。
    """

    def __init__(self) -> None:
        self._static = _StaticAIConfig()  # 初始化时加载一次静态配置

        # 定义动态属性的获取规则：属性名 -> (配置中心路径, 类型)
        self._dynamic_attr_map = {
            "timeout": ("global.network_timeout", float),
            "model_name": ("ai.model_name", str),
            "api_key": ("ai.api_key", str),
            "temperature": ("ai.temperature", float),
            "group_triggers": ("chore.triggers", list),
            "cleanup_time": ("data.clearup", float),
            "waiting_time": ("data.waiting", float),
            "init": ("chore.personality", str),
        }

    @error_guard("AI 配置读取", reraise=True)
    def __getattr__(self, name: str) -> Any:
        """拦截属性访问

        静态优先，动态实时读取
        """
        # ConfigError 由装饰器发信号后上抛；AttributeError 原样透出
        if hasattr(self._static, name):
            return getattr(self._static, name)

        # 如果是动态属性，则实时获取
        if name in self._dynamic_attr_map:
            attr_path, attr_type = self._dynamic_attr_map[name]
            value = config_manager.get(attr_path, attr_type)

            # 在这里进行值的后处理
            if name == "group_triggers":
                return tuple(value)
            if name == "cleanup_time":
                return value * _HOUR_SECONDS
            if name == "waiting_time":
                return value * _HOUR_SECONDS
            if name == "init":
                return tuple([build_message("system", value)])

            return value

        raise AttributeError(f"AIConfig 对象没有属性 '{name}'")


ai_config = _DynamicAIConfig()  # 全局配置单例
