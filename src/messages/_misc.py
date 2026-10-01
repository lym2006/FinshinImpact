# src/messages/_misc.py
"""全局杂项文案"""


class MiscMessage:
    """全局杂项文案

    - 跨窗口的零散话术与工具栏装配数据聚合入口
    """

    # 用：bot/__main__.py 单实例冲突弹窗
    ALREADY_RUNNING = "机器人已在运行，请勿重复启动。\n请先关闭已开的窗口，或使用「网络诊断」查看状态。"

    # 用：gui/__init__.py 主窗口工具栏（文案, 按钮键）
    TOOLBAR_BUTTONS: list[tuple[str, str]] = [
        ("修改配置", "settings"),
        ("网络诊断", "diagnose"),
        ("查看日志", "log"),
        ("检查更新", "update"),
        ("清空仪表盘", "clear"),
        ("关闭机器人", "shutdown"),  # 该按钮应被隐藏
    ]
