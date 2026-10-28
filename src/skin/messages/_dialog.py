# src/skin/messages/_dialog.py
"""弹窗装配文案"""


class DialogMessage:
    """弹窗装配文案

    - 各弹窗的标题、按钮与提示语，供主题令牌代理引用
    - 成员以所属弹窗子域为前缀，表格状态符号归 MARK_ 段
    """

    # 用：theme SettingsDialogTheme 文案字段
    SETUP_TITLE = "修改配置"
    SETUP_TIP = "检测到配置有误，请修正后继续"
    SETUP_HINT = "留意带 ⚠ 的标签页，标题标红的即为出错字段"
    SETUP_VERIFIED_OK = "配置已验证通过"
    SETUP_HISTORY_RESET = "人设或主人已变更，全部对话历史与落盘记录已清空"
    SETUP_RESET = "恢复默认"
    SETUP_RESET_ICON = "↺"

    # 用：utils/config/_schema.py 代理模式下拉选项文案
    SETUP_MODE_AUTO = "自动（配置→系统→直连）"
    SETUP_MODE_CFG = "仅配置代理"
    SETUP_MODE_SYS = "仅系统代理"
    SETUP_MODE_DIRECT = "仅直连（代理软件开 TUN 时选这个）"

    # 用：settings 弹窗 chore 页人设按钮行与预览弹窗
    SETUP_PERSONA_TITLE = "人设预览"
    SETUP_PERSONA_LABEL = "人设正文"
    SETUP_PERSONA_PREVIEW = "预览人设"
    SETUP_PERSONA_RELOAD = "从文件重新加载"
    SETUP_PERSONA_RELOAD_SAME = "文件跟当前正文一样，什么都没换"
    SETUP_PERSONA_PENDING = "草稿尚未落盘，保存配置后生效"
    SETUP_PERSONA_DISCARDED = "人设草稿未保存，已丢弃"
    SETUP_PERSONA_FILE_CREATE_FAIL = "人设文件建不出来，检查目录是否可写"
    SETUP_PERSONA_CLOSE = "关闭"
    SETUP_PERSONA_EDIT = "编辑人设"
    SETUP_PERSONA_EDITOR_TITLE = "人设正文编辑"
    SETUP_PERSONA_EDITOR_TIP = (
        "正文里的 {OWNER_ID} 是主人 id 占位符，保存配置时自动填入，请勿改动\n"
        "别直接改实例人设文件，程序只在启动读它一次，改了不生效，还可能被这里的正文盖掉"
    )
    SETUP_PERSONA_USE_TEMPLATE = "用模板覆盖"
    SETUP_PERSONA_NO_TEMPLATE = "内置默认模板读不出"
    SETUP_PERSONA_TEMPLATE_SAME = "编辑框里的正文和模板一模一样，不用覆盖"
    SETUP_PERSONA_TEMPLATE_TITLE = "用模板覆盖前比对"
    SETUP_PERSONA_TEMPLATE_OK = "确认覆盖"
    SETUP_PERSONA_VIEW_DIFF = "查看变化"
    SETUP_PERSONA_DIFF_TITLE = "人设正文变更"
    SETUP_PERSONA_DIFF_ORI = "当前正文"
    SETUP_PERSONA_DIFF_MOD = "变更后"
    SETUP_PERSONA_CONFLICT_TITLE = "人设正文不一致"
    SETUP_PERSONA_CONFLICT_TEXT = "实例人设文件与程序生效的正文不一致，选一份继续"
    SETUP_PERSONA_CONFLICT_DISK = "用文件版本"
    SETUP_PERSONA_CONFLICT_APPLIED = "用生效版本"

    # 用：主窗弹窗与引导期选窗共用的按钮字段
    BTN_CANCEL = "取消"
    BTN_SAVE = "保存"
    BTN_EXIT = "退出程序"
    BTN_FINISH = "完成并保存"
    BTN_CONFIRM = "确认"
    BTN_VALIDATING = "校验中..."

    # 用：theme ShutdownDialogTheme 文案字段
    SHUTDOWN_TITLE = "确认退出"
    SHUTDOWN_MSG = "确定要关闭机器人并退出程序吗？"

    # 用：theme NoticeDialogTheme 文案字段
    NOTICE_TITLE = "提示"
    NOTICE_OK = "知道了"
    NOTICE_FATAL_TITLE = "致命错误"
    NOTICE_FATAL_HEAD = "程序遇到无法恢复的错误，即将退出"
    NOTICE_FATAL_OK = "确认并退出"
    NOTICE_NOT_CHANGED = "您未修改任何配置"

    # 用：theme NoticeDialogTheme 人设对账弹窗字段
    PERSONA_APPLY = "用默认人设覆盖"
    PERSONA_KEEP = "保留我的人设"

    # 用：theme ReleaseNotesDialogTheme 文案字段
    RELEASE_NOTES_TITLE = "版本变化"
    RELEASE_NOTES_LOADING = "正在拉取发布内容..."
    RELEASE_NOTES_READY = "已取到 {count} 个版本的发布说明"

    # 用：theme WaitDialogTheme 文案字段
    WAIT_TITLE = "请稍候"
    WAIT_CHECK = "正在检查版本..."

    # 用：theme CheckDialogTheme 校验轮字段
    CHECK_VERIFY_TITLE = "连通性校验"
    CHECK_VERIFY_HEAD = "正在校验连通性..."
    CHECK_VERIFY_HEAD_PASS = "连通性校验通过"
    CHECK_VERIFY_HEAD_FAIL = "连通性校验未通过"

    # 用：theme CheckDialogTheme 诊断轮字段
    CHECK_DIAG_TITLE = "网络诊断"
    CHECK_DIAG_HEAD = "正在网络诊断..."
    CHECK_DIAG_HEAD_PASS = "网络诊断完成"
    CHECK_DIAG_HEAD_FAIL = "网络诊断未通过"

    # 用：theme 五态基类的符号字段（诊断窗与校验窗共用）
    MARK_PENDING = "•"
    MARK_CHECKING = "…"
    MARK_OK = "✓"
    MARK_SKIP = "✓"  # 跳过行同样绿勾，详情文字区分
    MARK_FAIL = "✗"

    # 用：theme ChangeDialogTheme 文案字段
    CHANGE_TITLE = "确认变更"
    CHANGE_TIP = "以下配置将被修改，确认保存？"
    CHANGE_COL_KEY = "配置项"
    CHANGE_COL_ORI = "原配置"
    CHANGE_COL_MOD = "新配置"
    CHANGE_RETURN = "返回修改"
    CHANGE_CONFIRM = "确认保存"

    # 用：theme LinkDialogTheme 文案字段
    LINK_TITLE = "网络重连中"
    LINK_HEAD = "链路已断开，正在等待恢复"
    LINK_ELAPSED = "已断线 {timer}"
    LINK_RETRIES = "已尝试重连 {n} 次"
    LINK_MUTE = "本次不提示"
