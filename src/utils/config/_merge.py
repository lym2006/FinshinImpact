"""盘上配置与段表的对账

- 旧裸段的值搬进带来源前缀的段
- 模板新增的键补默认值，已有值不动
- 交出者撤项后的残留段与残留键点名不代删
"""

from copy import deepcopy

from ..logger import get_logger
from .models import AppConfigData, TabData
from .sources import AssembledSection, ConfigPlan

_logger = get_logger("Config")


def reconcile(plan: ConfigPlan, disk: AppConfigData) -> AppConfigData:
    """按段表整理盘上内容，交出装配顺序排好的整表

    - 段名一律换成带来源前缀的写法，搬走的裸段不再留顶层
    - 无人认领的段与值原样留着，各点一句名
    """
    merged: AppConfigData = {
        item.name: _section_values(item, disk) for item in plan.sections
    }
    moved = {legacy for item in plan.sections for legacy in item.legacy}
    for name in sorted(set(disk) - set(merged) - moved, key=lambda n: n.split(".")):
        _logger.info(f"配置段 {name} 不在任何来源交出的清单里，值原样留着")
        merged[name] = dict(disk[name])
    return merged


def _section_values(item: AssembledSection, disk: AppConfigData) -> TabData:
    """取一段的值

    - 盘上现值为准，缺的补默认值
    - 搬进来的与撤项的键点名
    """
    values: TabData = dict(disk.get(item.name, {}))
    for legacy in item.legacy:
        for key, value in (disk.get(legacy) or {}).items():
            # 新段已有的值为准，旧写法只把缺的补上
            values.setdefault(key, value)
        if legacy in disk:
            _logger.info(f"配置段 {legacy} 已搬进 {item.name}")

    keys = {str(fld.key) for fld in item.spec.fields}
    for fld in item.spec.fields:
        # deepcopy 隔离：防调用方就地改写交出模板里的共享默认对象
        values.setdefault(fld.key, deepcopy(fld.default))
    dead = [key for key in values if key not in keys]
    if dead:
        _logger.info(
            f"配置段 {item.name} 有交出者已撤的键：{'、'.join(dead)}，值原样留着"
        )
    return values
