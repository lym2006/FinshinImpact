"""跨仓用例的适配器在场判定

- 认已装的发行包：源码改动要重装才生效，在场与否以环境为准
"""

from importlib.metadata import PackageNotFoundError, distribution

_DIST = "finshin-adapter-tg"


def adapter_present() -> bool:
    """适配层是否真在这台机器上备好了内容"""
    try:
        distribution(_DIST)
    except PackageNotFoundError:
        return False
    return True
