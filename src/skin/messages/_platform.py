"""平台组件面板文案"""


class PlatformMessage:
    """平台组件面板文案

    - 三档段名、来源、动作与卸载话术
    - 有目录行的组件多出动作一行，已装包的再多出卸载一行
    """

    # 用：skin.theme 平台组件面板的窗名与弹窗标题
    TITLE = "平台组件"

    # 用：ui._guide._platform 三档的段名，按此次序排
    HEAD_LOCAL = "本机已有"
    HEAD_UPGRADABLE = "可更新"
    HEAD_ONLINE = "网络可装"

    # 用：ui._guide._platform 来源行的三种取值
    SOURCE_INSTALLED = "已装包"
    SOURCE_TREE = "本机源码仓"
    SOURCE_NONE = "本机没有"

    # 用：ui._guide._platform 每行的栏名
    LABEL_SOURCE = "来源"
    LABEL_VERSION = "版本"
    LABEL_DEPS = "接口包要求"
    LABEL_ACTION = "动作"

    # 用：ui._guide._platform 每块首行的组件名，两类都接发行件名
    NAME_SDK = "接口包 {name}"
    NAME_ADAPTER = "适配器 {name}"

    # 用：ui._guide._platform 版本行正文
    LINE_VERSIONS = "本机 {installed} ／ 在线 {available}"
    LINE_VERSIONS_ABSENT = "本机未安装 ／ 在线 {available}"
    LINE_ABSENT = "本机未安装"

    # 用：services.env_setup.platform_state 接口包要求行五态
    FLOOR_NONE = "未声明接口包版本要求"
    FLOOR_NO_SDK = "要求 {floor}，本机没装接口包"
    FLOOR_MET = "要求 {floor}，本机 {actual} 已满足"
    FLOOR_GAP = "要求 {floor}，本机 {actual} 未满足"
    FLOOR_UNREADABLE = "要求 {floor}，版本串读不懂"

    # 用：services.env_setup.platform_state 适配器那颗置灰时那句下一步
    NEED_SDK_INSTALL = "先装接口包"
    NEED_SDK_UPDATE = "先更新接口包"

    # 用：ui._guide._platform 动作栏两态
    BTN_INSTALL = "安装"
    BTN_APPLY = "更新"

    # 用：ui._guide._platform 底部一键与目录拒收段的行名
    BTN_UPDATE_ALL = "一键更新"
    REJECTS_HEAD = "目录里被拒的条目"

    # 用：ui._guide._platform 取数中的状态行与装卸的进度窗标题
    WAIT_CATALOG = "正在等在线目录…已过 {seconds} 秒"
    WAIT_INSTALL = "正在装 {name}…"
    WAIT_REMOVE = "正在卸 {name}…"

    # 用：services.env_setup.wheel_install 装完复核版本对不上
    APPLY_MISMATCH = "{name} 装完读到 {found}，不是要装的 {wanted}"

    # 用：ui._guide._platform 目录读不出时的那一行状态
    FETCH_FAILED = "在线目录读不到\n{reason}"

    # 用：ui._guide._platform 装完后的结果文案
    INSTALL_DONE = "{name} 已装好"
    INSTALL_PART_FAIL = "{name} 没装成\n{notes}"
    INSTALL_BLANK = "未报出原因"

    # 用：ui._guide._platform 已装包那一行的卸载按钮
    BTN_UNINSTALL = "卸载"

    # 用：ui._guide._platform 卸载前的确认与拦路文案
    UNINSTALL_ASK = (
        "要卸掉 {platform} 的适配器\n\n{names}\n\n别只平台的适配器与插件不受影响"
    )
    UNINSTALL_BLOCKED = "{platform} 还有 {count} 个实例\n先把实例删掉再卸适配器"
    UNINSTALL_DONE = "{platform} 的适配器已卸掉"

    # 用：services.env_setup.deps_install 逐只点名的卸不掉那句
    REMOVE_FAILED = "{name} 没卸掉"
