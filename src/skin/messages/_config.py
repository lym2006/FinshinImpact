"""配置面板文案"""


class ConfigMessage:
    """配置面板文案

    - 必填项提示与列表编辑文案
    """

    # 用：utils/config/_validator.py 必填项缺键或留空文案
    REQUIRED_MARK = "必填项未填写"

    # 用：ui/_dialogs/_settings/_list_widget.py 列表入口与增删按钮文本
    LIST_EDIT_TEXT = "编辑（{count} 条）"
    LIST_EDIT_TIP = "双击条目即可修改文字"
    LIST_ADD_TEXT = "添加新项"
    LIST_DEL_TEXT = "删除选中"
