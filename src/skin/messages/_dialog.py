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
    SETUP_RESET = "恢复默认"
    SETUP_RESET_ICON = "↺"

    # 用：utils/config/_schema.py 代理模式下拉选项文案
    SETUP_MODE_AUTO = "自动（配置→系统→直连）"
    SETUP_MODE_CFG = "仅配置代理"
    SETUP_MODE_SYS = "仅系统代理"
    SETUP_MODE_DIRECT = "仅直连（代理软件开 TUN 时选这个）"

    # 用：settings 弹窗 chore 页人设按钮行与预览弹窗
    SETUP_PERSONA_TITLE = "人设预览"
    SETUP_PERSONA_LABEL = "人设文件"
    SETUP_PERSONA_PREVIEW = "预览人设"
    SETUP_PERSONA_FROM_FILE = "正文来源：实例 persona.md"
    SETUP_PERSONA_FROM_TEMPLATE = "正文来源：内置默认模板，实例副本读不出"
    SETUP_PERSONA_MISSING = "正文来源：无，实例副本与内置模板都读不出"
    SETUP_PERSONA_SAME = "副本与默认模板一致"
    SETUP_PERSONA_OUTDATED = "默认模板已更新，副本还是旧版，点覆盖即换新"
    SETUP_PERSONA_EDITED = "副本与默认模板不同，覆盖会丢掉你的改动"
    SETUP_PERSONA_UNREADABLE = "副本或默认模板读不出，无法比对"
    SETUP_PERSONA_APPLIED = "正文已生效"
    SETUP_PERSONA_PENDING = "磁盘正文尚未生效，保存配置后启用"
    SETUP_PERSONA_FILE_CREATE_FAIL = "人设文件建不出来，检查目录是否可写"
    SETUP_PERSONA_OPEN = "打开人设文件"
    SETUP_PERSONA_OPEN_FAIL = "打开人设文件失败"
    SETUP_PERSONA_CLOSE = "关闭"

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

    # 用：配置面板仅人设正文变化时的保存提示
    PERSONA_RELOADED = "人设正文已按文件刷新"

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
