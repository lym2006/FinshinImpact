# src/utils/exceptions.py
"""
全局自定义异常

集中管理项目中所有的业务异常，避免循环导入问题
"""


class ConfigError(Exception):
    """配置文件缺失、格式错误或需要人工干预时抛出"""


class TaskStoppedError(Exception):
    """AI 任务被意外中断或停止时触发的异常"""
