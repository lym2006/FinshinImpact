"""发行件族名与在场读数

- 已装版本取包元数据，不在场交出空串
- 依赖声明串里取指定发行件的版本要求
"""

import importlib.metadata
import re
from collections.abc import Sequence

# 分发名口径与在线目录生成侧同值，两处改名必须同步
SDK_DISTRIBUTION = "finshin-sdk"

# 包名归一只认连字符，点号与下划线按同一个分隔算
_SEPARATOR_RUN = re.compile(r"[-_.]+")

# 依赖声明串里的发行件名、附加功能名与其后的版本要求
_PIN = re.compile(
    r"\s*(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*(?P<spec>.*)"
)

# 版本要求的开头字符，比较符与括号都算
_SPEC_START = re.compile(r"[<>=!~\[(]")

# 多条约束的排布次序，下限在前、上限在后
_CLAUSE_OPS = (">=", ">", "==", "~=", "!=", "<=", "<")

# 一条依赖声明里版本要求之后的附加条件
_MARKER_SEP = ";"


def _normalized(name: str) -> str:
    """把分发名归一成比对用的写法"""
    return _SEPARATOR_RUN.sub("-", name).strip().lower()


def installed_version(distribution: str) -> str:
    """取已装包的版本

    - 不在场交出空串
    """
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return ""


def requires_of(pins: Sequence[str], distribution: str) -> str:
    """取依赖声明里指定发行件的版本要求

    - 没声明交出空串
    - 多条约束按下限在前、上限在后排
    - 一条声明里的多条约束整串交出，比较符照原样留着
    - 没带比较符即没写版本要求，交出空串
    - 附加功能名与整条外面的括号不算版本要求
    """
    want = _normalized(distribution)
    for pin in pins:
        parts = _PIN.fullmatch(str(pin).split(_MARKER_SEP)[0])
        if parts is None or _normalized(parts["name"]) != want:
            continue
        spec = parts["spec"].strip().strip("()")
        return _ordered(spec) if _SPEC_START.match(spec) else ""
    return ""


def _ordered(spec: str) -> str:
    """把逗号分隔的多条约束按下限在前重排"""
    clauses = [item.strip() for item in spec.split(",") if item.strip()]
    clauses.sort(key=_clause_rank)

    return ",".join(clauses)


def _clause_rank(clause: str) -> int:
    """约束的排序档位

    - 认不出的写法排最后
    """
    return next(
        (index for index, op in enumerate(_CLAUSE_OPS) if clause.startswith(op)),
        len(_CLAUSE_OPS),
    )
