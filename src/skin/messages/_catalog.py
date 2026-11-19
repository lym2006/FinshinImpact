"""在线目录文案"""


class CatalogMessage:
    """在线目录异常文案

    - 目录坏段、坏行与取件各步失败的原因句
    """

    # 用：services/adapter_catalog.py 整份目录读不出内容时的说明行
    BROKEN = "在线目录读不出内容"

    # 用：services/adapter_catalog.py 目录里没有接口包那一段时的说明行
    SDK_MISSING = "目录里没有接口包那一段"

    # 用：services/adapter_catalog.py 条目行不是表时的说明行
    NOT_A_ROW = "有一行适配器条目不是表"

    # 用：services/adapter_catalog.py 条目行没写分发名时的点名替身
    NO_NAME = "没写分发名的适配器条目"

    # 用：services/adapter_catalog.py 点名某只发行件坏在哪一步的说明行骨架
    ITEM_REJECTED = "{name}：{reason}"

    # 用：services/adapter_catalog.py 必填键缺失或空值的原因句
    MISS_FIELD = "缺 {field}"

    # 用：services/adapter_catalog.py 指纹串形态不对的原因句
    BAD_SHA = "指纹不是 64 位十六进制串"

    # 用：services/adapter_catalog.py 下载地址形态不对的原因句
    BAD_URL = "下载地址不是 https 开头的完整串"

    # 用：services/adapter_catalog.py 平台码不在词表里时的说明行
    PLATFORM_UNKNOWN = "{code}：平台码不在认下来的名单里"

    # 用：services/adapter_catalog.py 同一平台码出现第二行时的说明行
    PLATFORM_DUP = "{code}：同一平台码出现第二行，只认先读到的那行"

    # 用：services/env_setup/wheel_fetch.py 直链末段取不出 wheel 文件名的原因句
    BAD_FILE_NAME = "直链末段取不出 wheel 文件名"

    # 用：services/env_setup/wheel_fetch.py 某个源取不到件时的原因句
    FETCH_FAILED = "{url} 取不到内容"

    # 用：services/env_setup/wheel_fetch.py 落盘件与目录指纹不符时的原因句
    SHA_MISMATCH = "落盘指纹与目录不符"

    # 用：services/env_setup/wheel_fetch.py 写不进盘时的原因句
    WRITE_FAILED = "落盘失败"

    # 用：services/env_setup/wheel_install.py 某只 wheel 装不进运行环境时的说明行
    INSTALL_FAILED = "{name} 装不进运行环境"
