# src/plugins/AI/config.py
"""AI 配置

- 固定取值落在类属性上
- 配置中心字段按访问实时读取
"""

from pathlib import Path
from typing import Any, TypeVar

from bot.error_guard import error_guard
from core.domain import ConfigKey, ConfigSection
from core.domain.ids import ConfigPath
from utils import config_manager
from utils.paths import RECORDS_DIR
from utils.persona import build_persona

from .utils import build_message

T = TypeVar("T")

# 配置中心按天/按小时填，运行期换算成秒
_HOUR_SECONDS = 60 * 60
_DAY_SECONDS = 24 * _HOUR_SECONDS


class _DynamicAIConfig:
    """配置取用出口

    - 配置中心字段每次访问现读，改完不必重启
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

    @error_guard("AI 配置读取", reraise=True)
    def _read(self, path: ConfigPath, expected: type[T]) -> T:
        """按点路径取配置中心的原始值"""
        return config_manager.get(path, expected)

    def __getattr__(self, name: str) -> Any:
        """不存在的属性名一律拦下"""
        raise AttributeError(f"AIConfig 对象没有属性 '{name}'")

    @property
    def api_key(self) -> str:
        """模型密钥"""
        return self._read(ConfigKey.API_KEY.path(ConfigSection.AI), str)

    @property
    def temperature(self) -> float:
        """采样温度"""
        return self._read(ConfigKey.TEMPERATURE.path(ConfigSection.AI), float)

    @property
    def group_triggers(self) -> tuple[str, ...]:
        """群聊触发词"""
        return tuple(self._read(ConfigKey.TRIGGERS.path(ConfigSection.CHORE), list))

    @property
    def lost_lines(self) -> tuple[str, ...]:
        """停机交代话术，空行滤掉"""
        lines = self._read(ConfigKey.LOST_LINES.path(ConfigSection.CHORE), list)
        return tuple(line for line in lines if line.strip())

    @property
    def keep_seconds(self) -> float:
        """记录保留时长，配置按天填"""
        days = self._read(ConfigKey.RECORD_KEEP.path(ConfigSection.DATA), float)
        return days * _DAY_SECONDS

    @property
    def waiting_time(self) -> float:
        """清理轮间隔，配置按小时填"""
        hours = self._read(ConfigKey.WAITING.path(ConfigSection.DATA), float)
        return hours * _HOUR_SECONDS

    @property
    def init(self) -> tuple[dict[str, str], ...]:
        """当前人设那条系统轮"""
        owner = self._read(ConfigKey.OWNER.path(ConfigSection.CHORE), str)
        return (build_message("system", build_persona(owner)),)


ai_config = _DynamicAIConfig()  # 全局配置单例
