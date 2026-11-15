"""版本比对

- PEP440 口径只在这一处使用
- 比下限与比新旧都把读不懂的版本串交成 None，拒不拒由调用方判
"""

from packaging.version import InvalidVersion, Version


def is_upgrade(local: str, remote: str) -> bool | None:
    """在线版本是否比本机新

    - 任一侧的版本串读不懂交出 None
    """
    try:
        return Version(local) < Version(remote)
    except InvalidVersion:
        return None


def floor_met(actual: str, floor: str) -> bool | None:
    """实际版本是否达到要求的下限

    - 任一侧的版本串读不懂交出 None，拒载与否由调用方判
    """
    try:
        return Version(actual) >= Version(floor)
    except InvalidVersion:
        return None
