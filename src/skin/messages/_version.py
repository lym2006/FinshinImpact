"""版本比对文案

- 异常填充话术与等待窗中断文案
"""


class VersionMessage:
    """版本比对文案

    - 版本异常的错误正文填充值与中断话术
    """

    # 用：skin/theme/_dialogs.py 等待窗的兜底字段
    CRASH = "检查异常中断：{err}，详情见日志"

    # 用：utils/check/_version.py 抛版本异常时的错误正文填充值
    LOCAL_MISS = "项目文件不存在"
    LOCAL_BROKEN = "读取失败"
    REMOTE_BROKEN = "读取未知错误"
