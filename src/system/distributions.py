"""发行件族名与在场读数

- 接口包分发名只在这一处写
- 已装版本取包元数据，不在场交出空串
- 依赖声明串里取指定发行件的版本下限
"""

import importlib.metadata
import re
from collections.abc import Sequence

# 分发名口径与在线目录生成侧同值，两处改名必须同步
SDK_DISTRIBUTION = "finshin-sdk"

# 包名归一只认连字符，点号与下划线按同一个分隔算
_SEPARATOR_RUN = re.compile(r"[-_.]+")

# 依赖声明串里名字与版本要求的分界
_SPEC_START = re.compile(r"[<>=!~\[(]")

# 一条依赖声明里版本要求之后的附加条件
_MARKER_SEP = ";"

# 版本下限的比较符，长写法先配
_FLOOR_OPS = (">=", "<=", "==", "~=", ">", "<", "~", "=")


def _normalized(name: str) -> str:
    """把分发名归一成比对用的写法"""
    return _SEPARATOR_RUN.sub("-", name).strip().lower()


def installed_version(distribution: str) -> str:
    """取已装包的版本，不在场交出空串"""
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return ""


def floor_of(pins: Sequence[str], distribution: str) -> str:
    """从依赖声明里取指定发行件的版本下限，没声明交出空串

    - 一条声明带多个约束只认头一个约束
    - 比较符写作何种形态都剥掉，交出裸版本号
    """
    want = _normalized(distribution)
    for pin in pins:
        text = str(pin).split(_MARKER_SEP)[0]
        found = _SPEC_START.search(text)
        if found is None or _normalized(text[: found.start()]) != want:
            continue
        return _strip_op(text[found.start() :].split(",")[0].strip().strip("()"))
    return ""


def _strip_op(spec: str) -> str:
    """剥掉比较符交出版本号，没带比较符交出空串"""
    return next(
        (spec[len(op) :].strip() for op in _FLOOR_OPS if spec.startswith(op)), ""
    )
