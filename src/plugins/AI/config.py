# src/plugins/AI/config.py
"""AI 配置

- 提供静态默认值与动态配置入口
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from bot.error_guard import error_guard
from core.domain import ConfigKey, ConfigSection
from core.domain.ids import ConfigPath
from utils import config_manager
from utils.paths import RECORDS_DIR
from utils.persona import build_persona

from .utils import build_message


@dataclass(frozen=True)
class _StaticAIConfig:
    """静态配置

    - 存放固定不变的值
    """

    # 路径配置
    record_dir: Path = RECORDS_DIR

    # 硬编码模型行为
    model_name: str = "qwen3.7-flash"
    think_mode: tuple[tuple[str, Any], ...] = (("enable_thinking", False),)

    # 上文压缩：超触发线即压，尾部保留指定轮数原文
    summary_trigger_tokens: int = 16384
    summary_keep_rounds: int = 6

    # 摘要体量：软线提示调阈值，硬线按句子边界裁掉前段
    summary_soft_limit: int = 512
    summary_hard_limit: int = 1024

    # API 与模型基础配置
    base_url: str = "https://maas.qianwenaiapi.com/compatible-mode/v1"
    request_path: str = "/chat/completions"


_HOUR_SECONDS = 60 * 60
_DAY_SECONDS = 24 * _HOUR_SECONDS


class _DynamicAIConfig:
    """动态配置代理

    - 属性访问实时透传配置中心
    """

    def __init__(self) -> None:
        # 初始化时加载一次静态配置
        self._static = _StaticAIConfig()

        # 定义动态属性的获取规则：属性名 -> (配置中心路径, 类型)
        self._dynamic_attr_map: dict[str, tuple[ConfigPath, type]] = {
            "timeout": (ConfigKey.NETWORK_TIMEOUT.path(ConfigSection.GLOBAL), float),
            "api_key": (ConfigKey.API_KEY.path(ConfigSection.AI), str),
            "temperature": (ConfigKey.TEMPERATURE.path(ConfigSection.AI), float),
            "group_triggers": (ConfigKey.TRIGGERS.path(ConfigSection.CHORE), list),
            "keep_seconds": (ConfigKey.RECORD_KEEP.path(ConfigSection.DATA), float),
            "waiting_time": (ConfigKey.WAITING.path(ConfigSection.DATA), float),
            "init": (ConfigKey.OWNER.path(ConfigSection.CHORE), str),
        }

    @error_guard("AI 配置读取", reraise=True)
    def __getattr__(self, name: str) -> Any:
        """拦截属性访问

        - 静态优先，动态实时读取
        """
        # ConfigError 由装饰器发信号后上抛，AttributeError 原样透出
        if hasattr(self._static, name):
            return getattr(self._static, name)

        # 如果是动态属性，则实时获取
        if name in self._dynamic_attr_map:
            attr_path, attr_type = self._dynamic_attr_map[name]
            value = config_manager.get(attr_path, attr_type)

            # 在这里进行值的后处理
            match name:
                case "group_triggers":
                    return tuple(value)
                case "keep_seconds":
                    return value * _DAY_SECONDS
                case "waiting_time":
                    return value * _HOUR_SECONDS
                case "init":
                    return tuple([build_message("system", build_persona(value))])

            return value

        raise AttributeError(f"AIConfig 对象没有属性 '{name}'")


ai_config = _DynamicAIConfig()  # 全局配置单例
