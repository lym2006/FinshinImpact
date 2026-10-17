# src/messages/_engine.py
"""引擎与链路文案"""


class EngineMessage:
    """引擎与链路文案

    - 覆盖引擎装配、轮询启停、插件注册与链路断连恢复的面板短句
    """

    # 用：bot/_managers/_service.py 构建适配器前
    CREATING = "正在创建引擎..."

    # 用：bot/_service.py 拉起服务线程前
    STARTING = "正在启动引擎..."

    # 用：bot/_managers/_service.py 服务线程就绪后的收尾行
    STARTED = "引擎启动成功"

    # 用：bot/_service.py 重复启动的拦截行
    ALREADY_RUNNING = "引擎启动失败: 已在运行"

    # 用：bot/_managers/_service.py 停旧服务前的面板行
    STOPPING = "正在停止引擎..."

    # 用：bot/_service.py 轮询任务开场行
    POLLING_START = "正在启动轮询..."

    # 用：bot/_service.py 轮询被外部取消行
    POLLING_CANCELLED = "轮询被外部取消"

    # 用：bot/_managers/_service.py 插件注册结算行
    PLUGINS_DONE = "插件注册完成，共 {n} 项"

    # 用：bot/_managers/_service.py 逐插件成功行
    PLUGIN_OK = "[{index}/{n}] 插件 {name} 注册成功"

    # 用：bot/_managers/_service.py 逐插件失败行，reason 取自注册报告
    PLUGIN_FAIL = "[{index}/{n}] 插件 '{name}' {reason}"

    # 用：utils/network/_link.py 断连周期首行
    DOWN = "引擎断线：等待网络恢复"

    # 用：utils/network/_link.py 重连进度行，span 为面板时长短串、n 为累计尝试次数
    RETRYING = "重连中：已断 {span}，第 {n} 次尝试"

    # 用：utils/network/_link.py 断连周期收尾行，span 为面板时长短串、n 为重试次数
    RECOVERED = "网络恢复成功：断线 {span}，重试 {n} 次"
