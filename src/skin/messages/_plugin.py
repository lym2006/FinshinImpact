# src/skin/messages/_plugin.py
"""插件设置面板文案"""


class PluginMessage:
    """插件设置面板文案

    - 面板标题、插件行文案、保存结算与缺库提示的全部话术
    """

    # 用：bootstrap._plugin._panel 窗口标题
    TITLE = "插件设置（实例：{code}）"

    # 用：bootstrap._plugin._panel 核心行勾选位替代文字
    ROW_CORE = "必选"

    # 用：bootstrap._plugin._panel 行尾状态标签
    STATUS_INSTALLED = "已装"
    STATUS_MISSING = "缺 {count} 个库"
    STATUS_DEV_SKIP = "开发模式请手动安装"

    # 用：bootstrap._plugin 启动结算进度窗标题
    PROGRESS_RUNTIME = "正在结算插件依赖"

    # 用：services.env_setup.deps_install 同步两阶段提示行
    STAGE_COMPILE = "正在解析依赖闭包…"
    STAGE_SYNC = "正在重建环境…"

    # 用：bootstrap._plugin 启动结算逐插件安装行
    STARTUP_INSTALL = "正在为 {name} 安装依赖…"

    # 用：bootstrap._plugin 启动结算失败弹窗标题与正文
    SETTLE_TITLE = "插件依赖结算"
    STARTUP_FAIL = "以下插件依赖安装失败，已自动禁用\n{plugins}\n失败项\n{items}\n下次启动会自动重试"

    # 用：bootstrap._plugin._panel 底栏按钮行
    BTN_SAVE = "保存"
    BTN_SAVE_START = "保存并启动"

    # 用：services.env_setup.subprocess_ops 换源重试行
    INDEX_RETRY = "换源重试（第 {try_count} 次）：{url}"
    INDEX_RETRY_NOTE = "上方报错无需处理，程序正在自动切换镜像源"

    # 用：services.env_setup.subprocess_ops 与 _progress 心跳行协议标记（行首符，后跟空格）
    HEARTBEAT_MARK = "⏳"

    # 用：services.env_setup.subprocess_ops 无输出静默期心跳行（进度窗原位刷新）
    HEARTBEAT = HEARTBEAT_MARK + " 已等待 {seconds} 秒…"

    # 用：services.env_setup.subprocess_ops 子进程失败摘要行
    PROC_FAIL = "执行未成功：{reason}"
    PROC_FAIL_FALLBACK = "原因详见运行日志插件装卸记录"

    # 用：bootstrap._plugin._progress 任务异常中止行
    TASK_FAIL = "任务异常中止，详情见运行日志"

    # 用：services.env_setup.assets 内核镜像回退行
    CDN_FALLBACK = "npmmirror 不可用，已回退官方源重试，上方报错无需处理"

    # 用：services.env_setup.assets 资源声明非法行
    ASSET_BAD = "资源声明非法，应为「模块名 资源名」两段：{asset}"

    # 用：services.env_setup.subprocess_ops 开发模式降级手动命令
    DEV_MANUAL = "开发模式请在虚拟环境下手动执行：\n{commands}"
    DEV_SYNC = "开发模式不支持同步依赖，请在虚拟环境手动操作"

    # 用：bootstrap._plugin._maintain 全局同步大警告
    SYNC_WARNING = (
        "同步将重建环境为与清单一致\n已装的开发工具会保留，其余残留包会被移除，耗时较长"
    )

    # 用：bootstrap._plugin._maintain 同步进度窗标题
    PROGRESS_SYNC = "同步重建环境"

    # 用：bootstrap._plugin._maintain 依赖管理下拉两项
    MENU_SYNC = "同步重建环境"
    MENU_CACHE = "清理下载缓存"

    # 用：bootstrap._plugin._maintain 清缓存大警告
    CACHE_WARNING = (
        "将清空 uv 下载缓存，释放磁盘占用\n清空后下次装库或同步需重新联网下载，耗时较长"
    )

    # 用：bootstrap._plugin._maintain 清缓存进度窗标题
    PROGRESS_CACHE = "清理下载缓存"

    # 用：bootstrap._plugin._progress 进度窗底栏按钮两态
    BTN_RUNNING = "进行中…"
    BTN_DONE = "完成"
