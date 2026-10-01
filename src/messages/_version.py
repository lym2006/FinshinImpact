# src/messages/_version.py
"""版本检测文案"""


class VersionMessage:
    """版本检测文案

    - 升级检查回执与异常填充话术的聚合入口
    """

    # 用：gui/_theme/_dialogs.py WaitDialogConfig 回执字段
    UP_TO_DATE = "已是最新版本：v{ver}"

    # 用：gui/_theme/_dialogs.py WaitDialogConfig 兜底字段
    CRASH = "检查异常中断：{err}，详情见日志"

    # 用：utils/_version_checker.py 抛版本异常时的 {msg} 填充值
    LOCAL_MISS = "项目文件不存在"
    LOCAL_BROKEN = "读取失败"
    REMOTE_BROKEN = "读取未知错误"
