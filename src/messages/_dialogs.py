# src/messages/_dialogs.py
"""弹窗装配文案（内部实现）"""


class DialogMessage:
    """弹窗装配文案

    各专属弹窗的标题、按钮与提示语聚合入口，供主题令牌代理引用。
    成员一律以所属弹窗子域为前缀，五态表格符号收进 MARK_ 段。
    """

    # ==================== 配置编辑弹窗 ====================

    # 用：theme SettingsDialogConfig 文案字段
    SETUP_TITLE = "修改配置"
    SETUP_TIP = "检测到配置有误，请修正后继续"
    SETUP_HINT = "留意带 ⚠ 的标签页，标题标红的即为出错字段"
    SETUP_VERIFIED_OK = "配置已验证通过"
    SETUP_RESET = "恢复默认"
    SETUP_RESET_ICON = "↺"

    # ==================== 通用按钮文案 ====================

    # 用：settings/shutdown/verify 等弹窗的按钮字段
    BTN_CANCEL = "取消"
    BTN_SAVE = "保存"
    BTN_EXIT = "退出程序"
    BTN_FINISH = "完成并保存"
    BTN_CONFIRM = "确认"
    BTN_VALIDATING = "校验中..."

    # ==================== 退出确认弹窗 ====================

    # 用：theme ShutdownDialogConfig 文案字段
    SHUTDOWN_TITLE = "确认退出"
    SHUTDOWN_MSG = "确定要关闭机器人并退出程序吗？"

    # ==================== 统一通知弹窗 ====================

    # 用：theme NoticeDialogConfig 文案字段
    NOTICE_TITLE = "提示"
    NOTICE_OK = "知道了"
    NOTICE_FATAL_TITLE = "致命错误"
    NOTICE_FATAL_HEAD = "程序遇到无法恢复的错误，即将退出"
    NOTICE_FATAL_OK = "确认并退出"
    NOTICE_NOT_CHANGED = "您未修改任何配置"

    # ==================== 忙碌等待弹窗 ====================

    # 用：theme WaitDialogConfig 文案字段
    WAIT_TITLE = "请稍候"
    WAIT_CHECK = "正在检查版本更新..."

    # ==================== 检查进度窗 ====================

    # 用：theme CheckDialogConfig 校验轮字段
    CHECK_VERIFY_TITLE = "连通性校验"
    CHECK_VERIFY_HEAD = "正在校验连通性..."
    CHECK_VERIFY_HEAD_PASS = "连通性校验通过"
    CHECK_VERIFY_HEAD_FAIL = "连通性校验未通过"

    # 用：theme CheckDialogConfig 诊断轮字段
    CHECK_DIAG_TITLE = "网络诊断"
    CHECK_DIAG_HEAD = "正在网络诊断..."
    CHECK_DIAG_HEAD_PASS = "网络诊断完成"
    CHECK_DIAG_HEAD_FAIL = "网络诊断未通过"

    # ==================== 五态表格符号（诊断窗与校验窗共用） ====================

    # 用：theme 五态基类的符号字段
    MARK_PENDING = "•"
    MARK_CHECKING = "…"
    MARK_OK = "✓"
    MARK_SKIP = "✓"  # 跳过行同样绿勾，详情文字区分
    MARK_FAIL = "✗"

    # ==================== 变更确认弹窗 ====================

    # 用：theme ChangeDialogConfig 文案字段
    CHANGE_TITLE = "确认变更"
    CHANGE_TIP = "以下配置将被修改，确认保存？"
    CHANGE_COL_KEY = "配置项"
    CHANGE_COL_ORI = "原配置"
    CHANGE_COL_MOD = "新配置"
    CHANGE_RETURN = "返回修改"
    CHANGE_CONFIRM = "确认保存"
