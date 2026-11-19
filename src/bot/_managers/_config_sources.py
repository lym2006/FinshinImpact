"""配置来源清单

- 平台交出的来源、各已启用插件自己交出的来源与本体认领的来源拼成装配用的来源清单
- 标题跟字段表都由交出者给，本体只给自己那一份
- 插件装载不成的那一只不进配置
"""

from finshin_sdk.domain import (
    SECTIONS_BY_PLATFORM,
    ConfigKey,
    ConfigSection,
    FieldSpec,
    PluginFileName,
    SectionSpec,
)
from utils.config import ConfigSource, SourceKind
from utils.logger import get_logger
from utils.paths import PLATFORM, PROFILE_DIR
from utils.plugin import enabled_manifests, load_plugin

from .._adapter_host import parts_for

_logger = get_logger("Config")

# 本体这份来源：标题进面板左列，段表就是数据与运维一页
_CORE_TITLE = "Bot 设置"

_DATA_SECTION = SectionSpec(
    section=ConfigSection.DATA,
    title="记录与运维",
    fields=(
        FieldSpec(
            section=ConfigSection.DATA,
            key=ConfigKey.RECORD_KEEP,
            value_type=float,
            default=30.0,
            label="记录保留（天）",
            desc="取值范围 1~3650，闲置超过这个天数的对话记录与群上下文一并删除",
            bounds=(1.0, 3650.0),
        ),
        FieldSpec(
            section=ConfigSection.DATA,
            key=ConfigKey.WAITING,
            value_type=float,
            default=0.5,
            label="检测间隔（小时）",
            desc="取值范围 0.1~720，间隔多久检测一次后台任务",
            bounds=(0.1, 720.0),
        ),
    ),
)


def config_sources() -> tuple[ConfigSource, ...]:
    """配置来源清单拼装

    - 平台、已启用插件、本体依次成序
    - 来源顺序即面板大类的行序，段内顺序照交出者给的顺序
    """
    return (_adapter_source(), *_plugin_sources(), _core_source())


def _adapter_source() -> ConfigSource:
    """本平台适配器交出的来源"""
    return ConfigSource(
        kind=SourceKind.ADAPTER,
        code=str(PLATFORM),
        title=parts_for(PLATFORM).title,
        sections=SECTIONS_BY_PLATFORM[PLATFORM],
    )


def _core_source() -> ConfigSource:
    """本体认领的那一段"""
    return ConfigSource(
        kind=SourceKind.CORE,
        code="",
        title=_CORE_TITLE,
        sections=(_DATA_SECTION,),
    )


def _plugin_sources() -> tuple[ConfigSource, ...]:
    """已启用插件交出的来源

    - 按启用序列排
    """
    sources: list[ConfigSource] = []
    for manifest in enabled_manifests(PROFILE_DIR / PluginFileName.STATE):
        try:
            declared = load_plugin(manifest).source_declaration()
        except Exception as e:
            _logger.error(
                f"插件 {manifest.name} 装载失败，它交出的配置段不进配置：{type(e).__name__}"
            )
            continue
        sources.append(
            ConfigSource(
                kind=SourceKind.PLUGIN,
                code=manifest.name,
                title=declared.title,
                sections=declared.sections,
            )
        )
    return tuple(sources)
