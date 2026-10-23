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

    # 命令
    CMD_NOT_FOUND = "命令不存在，请使用 /help "
    CMD_FORMAT_ERROR = "格式错误"
    CMD_USAGE = "可用输入：{inputs}"
    CMD_NO_PERMISSION = "没有权限使用该命令"

    # 命令授权
    GRANT_USAGE = "用法：/grant <用户 id>"
    UNGRANT_USAGE = "用法：/ungrant <用户 id>"
    GRANT_ADDED = "已授权 {id} 使用管理命令"
    GRANT_EXISTS = "{id} 已在授权名单里"
    UNGRANT_REMOVED = "已撤销 {id} 的管理权限"
    UNGRANT_MISSING = "授权名单里没有 {id}"

    # 历史记录
    HISTORY_EMPTY = "暂无历史记录"
    HISTORY_CAPTION = "📄 这是您最近的对话历史记录"
    HISTORY_MEMORY_CLEARED = "记忆清除成功"

    # AI 对话
    AI_UNAVAILABLE = "AI 对话服务暂不可用"
