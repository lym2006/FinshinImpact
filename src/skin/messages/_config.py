# src/skin/messages/_config.py
"""配置面板文案"""


class ConfigMessage:
    """配置面板文案

    - 大类与页签标题、字段标题与说明
    - 必填与前置项失败的占位标记
    """

    # 用：utils/config/_schema.py 组装左侧大类标题
    GROUP_TITLES = {
        "bot": "Bot 设置",
        "ai": "AI 设置",
    }

    # 用：utils/config/_schema.py 组装页签标题
    TAB_TITLES = {
        "proxy": "连接与代理",
        "ai": "模型",
        "chore": "主人与触发",
        "data": "记录与运维",
    }

    # 用：utils/config/_schema.py 组装字段标题
    LABELS = {
        "proxy_mode": "代理模式",
        "proxy": "代理",
        "api_key": "API Key",
        "temperature": "温度",
        "owner": "主人",
        "triggers": "触发词",
        "lost_lines": "停机交代话术",
        "record_keep": "记录保留（天）",
        "waiting": "检测间隔（小时）",
    }

    # 用：utils/config/_schema.py 组装字段说明
    DESCS = {
        "proxy_mode": "自动逐项尝试配置→系统→直连。单路档只校验选定一路，代理软件开 TUN 时选仅直连",
        "proxy": "自动与仅配置代理两档使用该项，其余模式锁定本项",
        "api_key": "在千问 AI 平台自行创建并填入",
        "temperature": "取值范围 0~2，越高越有创造性，越低越稳定",
        "owner": "具有最高权限的用户 ID（注意实例对应的平台）",
        "triggers": "用户消息包含关键词触发 AI 回复，不区分大小写",
        "lost_lines": "重启时对遗失对话补一句说明，随机取一条，留空交给 AI 现写",
        "record_keep": "闲置超过这个天数的对话记录与群上下文一并删除",
        "waiting": "间隔多久检测一次后台任务",
    }

    # 用：utils/config/_validator.py 必填项缺键或留空文案
    REQUIRED_MARK = "必填项未填写"

    # 用：adapters/telegram/probe.py 与设置面板前置项失败占位
    PENDING_MARK = "暂未检测"

    # 用：ui/_dialogs/_settings/_list_widget.py 列表入口与增删按钮文本
    LIST_EDIT_TEXT = "编辑（{count} 条）"
    LIST_EDIT_TIP = "双击条目即可修改文字"
    LIST_ADD_TEXT = "添加新项"
    LIST_DEL_TEXT = "删除选中"
