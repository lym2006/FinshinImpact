# src/plugins/messages.py
"""用户文案

- 定义 Telegram 固定话术
- 定义命名占位与 .format() 约定
"""


class BotMessage:
    """Telegram 对话话术

    - 机器人侧用户可见文案单源
    - 成员按功能子域前缀归类
    """

    # 欢迎
    WELCOME = (
        "你好，我是基于aiogram开发的机器人Fool\n"
        '你可以输入"/help"获取功能列表，现在与我开始对话吧~'
    )

    # 命令
    CMD_NOT_FOUND = "命令不存在，请使用 /help "
    CMD_FORMAT_ERROR = "格式错误"

    # 历史记录
    HISTORY_EMPTY = "暂无历史记录"
    HISTORY_CAPTION = "📄 这是您最近的对话历史记录"
    HISTORY_MEMORY_CLEARED = "记忆清除成功"
    HISTORY_NO_CONTENT = "没有可展示的对话"

    # AI 对话
    AI_UNAVAILABLE = "AI 对话服务暂不可用"
