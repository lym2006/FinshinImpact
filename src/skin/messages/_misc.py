# src/skin/messages/_misc.py
"""全局杂项文案"""


class MiscMessage:
    """全局杂项文案

    - 跨窗口的零散话术与工具栏装配数据聚合入口
    """

    # 用：ui/_windows/_assembly.py 装配期崩溃弹窗
    CTRL_BIND_FAIL = "控制器绑定失败: 发现未在 UI 层定义的按钮标识 -> {keys}"
    CTRL_MISSING = "控制器缺失: UI 层定义了按钮，但缺少对应的 Controller -> {keys}"

    # 用：gui_guard 装饰器与日志控制器的面板报错
    GUARD_EXEC_ERROR = "执行 [{name}] 时发生错误"
    OPEN_LOGS_FAIL = "打开日志目录失败"
    UNKNOWN_ERROR = "发生未知错误"

    # 用：bootstrap 单实例冲突弹窗
    ALREADY_RUNNING = (
        "机器人已在运行，请勿重复启动\n请先关闭已开的窗口，或使用「网络诊断」查看状态"
    )

    # 用：ui/_dialogs 人设对账判不出未改动时的一键覆盖弹窗正文
    PERSONA_OUTDATED = (
        "内置默认人设已更新，本次没有替换\n"
        "点「用默认人设覆盖」可直接换新\n"
        "或自行打开人设文件对照修改"
    )

    # 用：ui/_dialogs 一键覆盖后的结果提示
    PERSONA_APPLIED = "已用最新默认人设覆盖你实例的人设文件"
    PERSONA_APPLY_FAIL = "人设文件覆盖失败，文件可能被占用或没有写入权限"

    # 用：bot/_managers 启动对账判为从未改动并自动换新版时的提示
    PERSONA_AUTO_APPLIED = (
        "内置默认人设已更新，你的副本从未改动，已自动换成新版\n"
        "全部对话历史与落盘记录已清空"
    )

    # 用：ui/_windows/_assembly.py 主窗口工具栏（文案, 按钮键）
    TOOLBAR_BUTTONS: list[tuple[str, str]] = [
        ("修改配置", "settings"),
        ("网络诊断", "diagnose"),
        ("查看日志", "log"),
        ("版本检查", "version"),
        ("版本变化", "release_notes"),
        ("清空仪表盘", "clear"),
        ("关闭机器人", "shutdown"),  # 该按钮应被隐藏
    ]
