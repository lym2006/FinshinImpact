# src/exceptions/_version.py
"""版本检查异常族

- 定义版本检查相关异常
"""

from ._base import BotError


class VersionError(BotError):
    """版本检查异常基类"""


class RemoteVersionError(VersionError):
    """远程版本检查异常"""

    def __init__(self, msg: str) -> None:
        super().__init__()
        self.msg = msg


class LocalVersionError(VersionError):
    """本地版本检查异常"""

    def __init__(self, msg: str) -> None:
        self.msg = msg
        super().__init__()


class NewVersionError(VersionError):
    """发现新版本异常"""

    def __init__(self, current_version: str, new_version: str) -> None:
        self.current_version = current_version
        self.new_version = new_version
        super().__init__()


VERSION_MAP = {
    RemoteVersionError: "远程版本检查异常：{msg}",
    LocalVersionError: "本地版本检查异常：{msg}",
    NewVersionError: (
        "\n新版本可用 v{current_version} -> v{new_version}"
        "\n重启本程序，点「是」即可自动更新"
    ),
}
