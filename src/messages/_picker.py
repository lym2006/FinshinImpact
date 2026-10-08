# src/messages/_picker.py
"""选 bot 窗口文案"""


class PickerMessage:
    """选 bot 窗口文案

    - 引导期实例选择、新建、编辑与删除的全部话术
    - 成员前缀即子窗归属，跨窗共用的表单归 FORM_、按钮归 BTN_
    """

    # 用：bootstrap._picker 选择窗
    TITLE = "选择机器人"
    HINT = "选择要启动的机器人，或新建一个"
    DELETE_CONFIRM = (
        "确定删除实例 {label}？\n该实例的配置、人设与数据一并删除，无法撤销"
    )
    DELETE_FAIL = "删除失败，文件可能正被占用\n请先关闭该实例的运行窗口后重试"

    # 用：bootstrap._slot 引导锁被占弹窗
    BUSY = "已有一个选择窗口在打开，请在该窗口操作"

    # 用：bootstrap._picker 各窗底部按钮
    BTN_NEW = "新建"
    BTN_EDIT = "编辑"
    BTN_DELETE = "删除"
    BTN_START = "启动"
    BTN_CANCEL = "取消"
    BTN_OK = "确定"

    # 用：bootstrap._picker 新建与编辑共用的表单
    FORM_TOKEN_LABEL = "Bot Token"
    FORM_TOKEN_HINT = "从 @BotFather 获取，形如 123456:ABCDEF"
    FORM_TOKEN_INVALID = "Token 格式不正确\n应形如 123456:ABCDEF"
    FORM_REMARK_LABEL = "备注名（可选）"

    # 用：bootstrap._picker 新建窗
    NEW_TITLE = "新建机器人"
    NEW_PLATFORM_LABEL = "平台"
    NEW_PLATFORM_TELEGRAM = "Telegram"
    NEW_PLATFORM_QQ = "QQ（暂未支持）"

    # 用：bootstrap._picker 编辑窗
    EDIT_TITLE = "编辑机器人"
    EDIT_PLATFORM_UNKNOWN = "该实例的平台无法识别\n可能不是本程序创建的实例"
    EDIT_TOKEN_CHANGED = (
        "Token 已换成另一个机器人\n"
        "身份码 {old} → {new}\n"
        "实例资产按身份码隔离\n"
        "无法就地改名，请新建实例"
    )
