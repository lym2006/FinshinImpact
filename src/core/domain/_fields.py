# src/core/domain/_fields.py
"""探测字段错误键词表

- 单源定义错误字典与面板标红共用的字段键
"""


class FieldKey:
    """探测错误字典的键协议

    - 区分 proxy 错与 token 错，禁止跨模块裸写
    - proxy 兼作面板标红字段键，token 不进面板仅作致命判定
    """

    PROXY = "proxy"
    TOKEN = "token"
