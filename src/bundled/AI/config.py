"""AI 配置

- 固定取值落在类属性上
- 配置中心字段按访问实时读取
- 交出本插件的来源声明与配置字段表
"""

from pathlib import Path
from typing import Any, TypeVar

from bot.error_guard import error_guard
from finshin_sdk.domain import (
    ConfigKey,
    ConfigPath,
    ConfigSection,
    FieldSpec,
    SectionSpec,
    SourceDeclaration,
)
from utils import config_manager
from utils.paths import RECORDS_DIR
from utils.persona import build_persona

from .utils import build_message

T = TypeVar("T")

# 配置中心按天/按小时填，运行期换算成秒
_HOUR_SECONDS = 60 * 60
_DAY_SECONDS = 24 * _HOUR_SECONDS

_MODEL_SECTION = SectionSpec(
    section=ConfigSection.AI,
    title="模型",
    fields=(
        FieldSpec(
            section=ConfigSection.AI,
            key=ConfigKey.API_KEY,
            value_type=str,
            default="",
            label="API Key",
            desc="在千问 AI 平台自行创建并填入",
            required=True,
        ),
        FieldSpec(
            section=ConfigSection.AI,
            key=ConfigKey.TEMPERATURE,
            value_type=float,
            default=0.7,
            label="温度",
            desc="取值范围 0~2，越高越有创造性，越低越稳定",
            bounds=(0.0, 2.0),  # OpenAI 兼容规范
        ),
    ),
)

_CHORE_SECTION = SectionSpec(
    section=ConfigSection.CHORE,
    title="主人与触发",
    fields=(
        FieldSpec(
            section=ConfigSection.CHORE,
            key=ConfigKey.OWNER,
            value_type=str,
            default="",
            label="主人",
            desc="具有最高权限的用户 ID（注意实例对应的平台）",
            required=True,
        ),
        FieldSpec(
            section=ConfigSection.CHORE,
            key=ConfigKey.TRIGGERS,
            value_type=list,
            default=[],
            label="触发词",
            desc="用户消息包含关键词触发 AI 回复，不区分大小写",
            required=True,
        ),
        FieldSpec(
            section=ConfigSection.CHORE,
            key=ConfigKey.LOST_LINES,
            value_type=list,
            default=[],
            label="停机交代话术",
            desc="重启时对遗失对话补一句说明，随机取一条，留空交给 AI 现写",
        ),
    ),
)

CONFIG_SOURCE = SourceDeclaration(
    title="AI 设置",
    sections=(_MODEL_SECTION, _CHORE_SECTION),
)


class _DynamicAIConfig:
    """配置取用出口

    - 配置中心字段每次访问现读
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
    def _read(self, item: ConfigPath, expected: type[T]) -> T:
        """按配置项身份取配置中心的原始值"""
        return config_manager.get(item, expected)

    def __getattr__(self, name: str) -> Any:
        """不存在的属性名一律拦下"""
        raise AttributeError(f"AIConfig 对象没有属性 '{name}'")

    @property
    def api_key(self) -> str:
        """模型密钥"""
        return self._read(ConfigKey.API_KEY.path("plugin.AI", ConfigSection.AI), str)

    @property
    def temperature(self) -> float:
        """采样温度"""
        return self._read(
            ConfigKey.TEMPERATURE.path("plugin.AI", ConfigSection.AI), float
        )

    @property
    def group_triggers(self) -> tuple[str, ...]:
        """群聊触发词"""
        return tuple(
            self._read(ConfigKey.TRIGGERS.path("plugin.AI", ConfigSection.CHORE), list)
        )

    @property
    def lost_lines(self) -> tuple[str, ...]:
        """停机交代话术"""
        lines = self._read(
            ConfigKey.LOST_LINES.path("plugin.AI", ConfigSection.CHORE), list
        )
        return tuple(line for line in lines if line.strip())

    @property
    def keep_seconds(self) -> float:
        """记录保留时长"""
        days = self._read(ConfigKey.RECORD_KEEP.path("core", ConfigSection.DATA), float)
        return days * _DAY_SECONDS

    @property
    def waiting_time(self) -> float:
        """清理轮间隔"""
        hours = self._read(ConfigKey.WAITING.path("core", ConfigSection.DATA), float)
        return hours * _HOUR_SECONDS

    @property
    def init(self) -> tuple[dict[str, str], ...]:
        """当前人设那条系统轮"""
        owner = self._read(ConfigKey.OWNER.path("plugin.AI", ConfigSection.CHORE), str)
        return (build_message("system", build_persona(owner)),)


ai_config = _DynamicAIConfig()  # 全局配置单例
