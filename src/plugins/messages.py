# src/plugins/messages.py
"""用户文案

- 定义 Telegram 固定话术
- 定义命名占位与 .format() 约定
"""

# ==================== 欢迎与基础 ====================

WELCOME = (
    "你好，我是基于aiogram开发的机器人Fool\n"
    '你可以输入"/help"获取功能列表，现在与我开始对话吧~'
)

# ==================== 帮助 ====================

CMD_NOT_FOUND = "命令不存在，请使用 /help "
CMD_FORMAT_ERROR = "格式错误"

# ==================== 黑名单 ====================

BLACKLIST_ADDED = "🚫 成功将用户 [{user}] 写入黑名单"
BLACKLIST_EXISTS = "🚫 用户 [{user}] 已存在黑名单内"
BLACKLIST_REMOVED = "成功将用户 [{user}] 移出黑名单"
BLACKLIST_ABSENT = "用户 [{user}] 不存在黑名单内"

# ==================== 历史记录 ====================

NO_HISTORY = "暂无历史记录"
HISTORY_CAPTION = "📄 这是您最近的对话历史记录"
MEMORY_CLEARED = "记忆清除成功"
NO_MD_CONTENT = "没有可展示的对话"

# ==================== 身份与系统指令 ====================

ASK_IDENTITY_NAME = "🎭 请输入新身份的名字"
ASK_IDENTITY_DESC = "📝 请输入新身份的描述"
ASK_SYSTEM_INPUT = "💻 你想以system身份输入什么内容"
ASK_TEXT = "请输入有效的文本"
ASK_RETEXT = "请重新输入文本"
IDENTITY_SET = "身份设置成功"
IDENTITY_READY = "{mention}，你的机器人「{name}」已准备好，可以开始对话。"
SYSTEM_INJECTED = "系统指令注入成功"

# ==================== AI 对话 ====================

AI_UNAVAILABLE = "AI 对话服务暂不可用"
