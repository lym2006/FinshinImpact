"""平台组件面板文案"""


class PlatformMessage:
    """平台组件面板文案

    - 三档段名、来源四档、来路三档、动作与卸载话术
    - 有目录行的组件多出动作一行，已装包的再多出卸载一行
    - 历史版本与本机安装包各展开一层，逐行报来路
    - 盘上的件分三档：目录里有这一版、本机记过指纹、两样都没有
    """

    # 用：skin.theme 平台组件面板的窗名与弹窗标题
    TITLE = "平台组件"

    # 用：ui._guide._platform 三档的段名，按此次序排
    HEAD_LOCAL = "本机已有"
    HEAD_UPGRADABLE = "可更新"
    HEAD_ONLINE = "网络可装"

    # 用：ui._guide._platform_block 来源行的四种取值
    SOURCE_TREE_INSTALLED = "本机源码仓（已装进环境）"
    SOURCE_TREE_ONLY = "本机源码仓（还没装进环境）"
    SOURCE_NONE = "本机没有"

    # 用：ui._guide._platform_block 来源行与历史版本行都写那一句
    LOCAL_INSTALLED = "本机已装"

    # 用：ui._guide._platform_block 来路行的三种取值
    LABEL_ORIGIN = "来路"
    ORIGIN_WHEEL = "本机已下载的件 {version}"
    ORIGIN_CATALOG = "在线目录 {version}"
    ORIGIN_TREE = "源码仓"

    # 用：ui._guide._platform_block 每行的栏名
    LABEL_SOURCE = "来源"
    LABEL_VERSION = "版本"
    LABEL_DEPS = "接口包要求"
    LABEL_ACTION = "动作"

    # 用：ui._guide._platform_block 每块首行的组件名，两类都接发行件名
    NAME_SDK = "接口包 {name}"
    NAME_ADAPTER = "适配器 {name}"

    # 用：ui._guide._platform_block 版本行正文
    LINE_VERSIONS = "本机 {installed} ／ 在线 {available}"
    LINE_VERSIONS_ABSENT = "本机未安装 ／ 在线 {available}"
    LINE_ABSENT = "本机未安装"

    # 用：services.env_setup.platform_state 接口包要求行五态，行首已有「接口包要求」标签
    REQUIRES_NONE = "未声明"
    REQUIRES_NO_SDK = "本机没装接口包"
    REQUIRES_MET = "{requires}，本机接口包 {actual} 已满足"
    REQUIRES_GAP = "{requires}，本机接口包 {actual} 未满足"
    REQUIRES_UNREADABLE = "声明的版本串读不懂"

    # 用：services.env_setup.platform_state 装某一版接口包被已装适配器挡住时那句
    SDK_RANGE_GAP = "这一版接口包超出已装适配器的要求"

    # 用：ui._guide._platform_text 目录里找不出一版可用的接口包时那句
    SDK_RANGE_NONE = "没有一版接口包满足已装适配器的要求"

    # 用：services.env_setup.platform_state 适配器那颗置灰时那句下一步
    NEED_SDK_INSTALL = "先装接口包"
    NEED_SDK_UPDATE = "先更新接口包"
    SDK_TOO_NEW = "接口包太新，适配器等新版"

    # 用：ui._guide._platform_block 动作栏两态
    BTN_INSTALL = "安装"
    BTN_APPLY = "更新"

    # 用：ui._guide._platform_block 两颗展开钮与钮旁的收起字
    BTN_HISTORY = "查看历史版本"
    BTN_WHEELS = "本机安装包"
    BTN_FOLD = "收起"

    # 用：ui._guide._platform_block 历史版本每一版的读数字与装旧版那颗
    BTN_INSTALL_VERSION = "装这版"
    WHEEL_CACHED = "已下载"

    # 用：ui._guide._platform_block 盘上件的逐份读数
    WHEEL_LISTED = "{name} 目录里有这一版，装它按目录给的指纹核"
    WHEEL_RECORDED = "{name} 本机下载时记过指纹，可直接装盘上那份"
    WHEEL_STRAY = "{name} 目录里没这一版本机也没记过，没有权威指纹可核，不给装"

    # 用：ui._guide._platform 底部一键与目录拒收段的行名
    BTN_UPDATE_ALL = "一键更新"
    REJECTS_HEAD = "目录里被拒的条目"

    # 用：ui._guide._platform 取数中的状态行
    WAIT_CATALOG = "正在等在线目录…已过 {seconds} 秒"

    # 用：ui._guide._platform_flow 装卸的进度窗标题
    WAIT_INSTALL = "正在装 {items}…"
    WAIT_REMOVE = "正在卸 {name}…"

    # 用：services.env_setup.wheel_install 装完复核版本对不上
    APPLY_MISMATCH = "{name} 装完读到 {found}，不是要装的 {wanted}"

    # 用：ui._guide._catalog_task 目录读不出时的那一行状态
    FETCH_FAILED = "在线目录读不到\n{reason}"

    # 用：ui._guide._platform_flow 装完后的结果文案
    INSTALL_DONE = "{items} 已装好"
    INSTALL_PART_FAIL = "{items} 没装成\n{notes}"
    INSTALL_BLANK = "未报出原因"

    # 用：ui._guide._platform_block 已装包那一行的卸载按钮
    BTN_UNINSTALL = "卸载"

    # 用：ui._guide._platform_flow 卸载前的确认与拦路文案
    UNINSTALL_ASK = (
        "确定要卸掉 {platform} 平台的适配器吗？\n\n其他平台的适配器与插件不受影响"
    )
    UNINSTALL_BLOCKED = "{platform} 平台还有 {count} 个实例\n先把实例删掉再卸适配器"
    UNINSTALL_DONE = "{platform} 平台的适配器已卸掉"

    # 用：services.env_setup.deps_install 逐只点名的卸不掉那句
    REMOVE_FAILED = "{name} 没卸掉"
