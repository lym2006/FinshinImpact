# src/exceptions/_initial.py
"""初始化异常族（内部实现）

- 定义文件与路径检查相关异常
"""

from ._base import BotError


class InitError(BotError):
    """初始化异常基类"""


# ==================== 版本检查异常 ====================


class VersionError(InitError):
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


INITIAL_MAP = {
    "Version": {
        RemoteVersionError: "远程版本检查异常：{msg}",
        LocalVersionError: "本地版本检查异常：{msg}",
        NewVersionError: "\n检测到新版本"
        "\n当前版本：{current_version}"
        "\n最新版本：{new_version}"
        "\n重启程序并在弹窗点「是」即可自动更新；"
        "\n多次失败请从 Releases 页手动下载整包",
    },
}
