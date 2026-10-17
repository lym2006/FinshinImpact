# src/messages/_config.py
"""配置面板文案"""


class ConfigMessage:
    """配置面板文案

    - 页签标题、字段标题与说明
    - 必填与前置项失败的占位标记
    """

    # 用：utils/config/_schema.py 组装页签标题
    TAB_TITLES = {
        "proxy": "Bot 基础设置",
        "global": "全局设置",
        "ai": "AI 模型设置",
        "chore": "AI 杂项设置",
        "data": "数据与运维",
    }

    # 用：utils/config/_schema.py 组装字段标题
    LABELS = {
        "proxy_mode": "代理模式",
        "proxy": "代理",
        "network_timeout": "超时（秒）",
        "api_key": "API Key",
        "temperature": "温度",
        "owner": "主人",
        "triggers": "触发词",
        "use_file": "人设文件",
        "personality": "人格设定",
        "clearup": "清理间隔（小时）",
        "waiting": "检测间隔（小时）",
    }

    # 用：utils/config/_schema.py 组装字段说明
    DESCS = {
        "proxy_mode": "自动逐项尝试配置→系统→直连。单路档只校验选定一路，代理软件开 TUN 时选仅直连",
        "proxy": "自动与仅配置代理两档使用该项，其余模式锁定本项",
        "network_timeout": "控制读取响应、写入请求及连接池等待的最大耗时",
        "api_key": "在千问 AI 平台自行创建并填入",
        "temperature": "取值范围 0~2，越高越有创造性，越低越稳定",
        "owner": "具有最高权限的用户 ID（平台已依据实例区分）",
        "triggers": "用户消息包含关键词（如 @Bot）触发 AI 回复，不区分大小写，双击编辑",
        "use_file": "勾选则从独立文件读取人设",
        "personality": "用于定义机器人的性格和行为",
        "clearup": "定期清理过期的会话数据",
        "waiting": "间隔多久检测一次后台任务",
    }

    # 用：utils/config/_validator.py 必填项缺键或留空文案
    REQUIRED_MARK = "必填项未填写"

    # 用：utils/check/_connectivity.py 与设置面板前置项失败占位
    PENDING_MARK = "暂未检测"
