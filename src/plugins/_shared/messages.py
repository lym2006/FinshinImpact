# src/plugins/_shared/messages.py
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
    GRANT_ASK_TARGET = "请发送要授权的 id，发 -1 取消"
    UNGRANT_ASK_TARGET = "请发送要撤销授权的 id，发 -1 取消"
    GRANT_BAD_TARGET = "这不是 id，请重试，或发 -1 取消"
    GRANT_RETRY_TARGET = "没记上，请重试，或发 -1 取消"
    GRANT_CANCELED = "已取消，授权名单未变"
    GRANT_ADDED = "已授权 {id}"
    GRANT_EXISTS = "{id} 已在授权名单，请重试，或发 -1 取消"
    UNGRANT_REMOVED = "已撤销授权 {id}"
    UNGRANT_MISSING = "{id} 不在授权名单，请重试，或发 -1 取消"
    ADMIN_COUNT = "授权名单共 {count} 人"
    ADMIN_LIST = "授权名单共 {count} 人：\n{ids}"
    ADMIN_EMPTY = "授权名单为空"
    ADMIN_READ_FAILED = "名单读取失败，稍后再试"

    # 历史记录
    HISTORY_EMPTY = "暂无历史记录"
    HISTORY_CAPTION = "📄 这是您最近的对话历史记录"
    HISTORY_MEMORY_CLEARED = "记忆清除成功"

    # AI 对话
    AI_UNAVAILABLE = "AI 对话服务暂不可用"
    CHAT_PRIVATE_DENIED = "私聊要主人或管理员，群里 @我 或说触发词就能聊"
