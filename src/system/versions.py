"""版本比对

- 读不懂的版本串一律交出 None，由调用方决定怎么处理
"""

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

# 约束里表示上限的两个比较符
_CEILING_OPS = ("<", "<=")


def is_upgrade(local: str, remote: str) -> bool | None:
    """在线版本是否比本机新

    - 任一侧的版本串读不懂交出 None
    """
    try:
        return Version(local) < Version(remote)
    except InvalidVersion:
        return None


def requires_met(actual: str, requires: str) -> bool | None:
    """实际版本是否落在要求的区间内

    - 要求串按逗号分成多条约束，差一条即不合
    - 任一侧读不懂交出 None
    """
    try:
        return Version(actual) in SpecifierSet(requires)
    except (InvalidSpecifier, InvalidVersion):
        return None


def over_ceiling(actual: str, requires: str) -> bool | None:
    """实际版本是否高出要求串里的上限

    - 要求串没写上限交出 False
    - 任一侧读不懂交出 None
    """
    try:
        number = Version(actual)
        clauses = SpecifierSet(requires)
    except (InvalidSpecifier, InvalidVersion):
        return None

    for clause in clauses:
        if clause.operator not in _CEILING_OPS:
            continue
        ceiling = Version(clause.version)

        # 「<0.2.0」这类上限，踩在那一档上即算高出
        if number > ceiling or (clause.operator == "<" and number == ceiling):
            return True

    return False
