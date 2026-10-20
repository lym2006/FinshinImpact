# src/core/domain/_record.py
"""落盘文件名主干

- 由容器段与用户段派生，不含键段冒号
"""

from .ids import ContainerKey, RecordStem


def make_record_stem(container: ContainerKey, user: str) -> RecordStem:
    """派生落盘文件名主干

    - 键段含冒号，Windows 文件名非法，不能直接落盘
    - 私聊出 u_{user}，群聊出 g_{群}_{user}
    """
    if container.startswith("g"):
        return RecordStem(f"g_{container[1:]}_{user}")
    return RecordStem(f"u_{user}")
