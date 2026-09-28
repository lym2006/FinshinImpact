# src/plugins/messages.py
"""用户文案

- 定义 Telegram 固定话术
- 定义命名占位与 .format() 约定
"""


class BotMessage:
    """Telegram 对话话术

    机器人侧用户可见文案单源，成员按功能子域前缀归类。
    """

    # ==================== 欢迎 ====================

    WELCOME = (
        "你好，我是基于aiogram开发的机器人Fool\n"
        '你可以输入"/help"获取功能列表，现在与我开始对话吧~'
    )

    # ==================== 命令 ====================

    CMD_NOT_FOUND = "命令不存在，请使用 /help "
    CMD_FORMAT_ERROR = "格式错误"

    # ==================== 黑名单 ====================

    BLACKLIST_ADDED = "🚫 成功将用户 [{user}] 写入黑名单"
    BLACKLIST_EXISTS = "🚫 用户 [{user}] 已存在黑名单内"
    BLACKLIST_REMOVED = "成功将用户 [{user}] 移出黑名单"
    BLACKLIST_ABSENT = "用户 [{user}] 不存在黑名单内"

    # ==================== 历史记录 ====================

    HISTORY_EMPTY = "暂无历史记录"
    HISTORY_CAPTION = "📄 这是您最近的对话历史记录"
    HISTORY_MEMORY_CLEARED = "记忆清除成功"
    HISTORY_NO_CONTENT = "没有可展示的对话"

    # ==================== 身份与系统指令 ====================

    IDENTITY_ASK_NAME = "🎭 请输入新身份的名字"
    IDENTITY_ASK_DESC = "📝 请输入新身份的描述"
    IDENTITY_ASK_SYSTEM = "💻 你想以system身份输入什么内容"
    IDENTITY_ASK_TEXT = "请输入有效的文本"
    IDENTITY_ASK_RETEXT = "请重新输入文本"
    IDENTITY_SET = "身份设置成功"
    IDENTITY_READY = "{mention}，你的机器人「{name}」已准备好，可以开始对话。"
    IDENTITY_SYSTEM_INJECTED = "系统指令注入成功"

    # ==================== AI 对话 ====================

    AI_UNAVAILABLE = "AI 对话服务暂不可用"
