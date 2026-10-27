# src/skin/theme/_settings.py
"""配置面板弹窗令牌

- 定义配置编辑弹窗与列表项的尺寸、文案与配色
- 弹窗话术字段一律代理引用 messages
"""

from dataclasses import dataclass

from ..messages import DialogMessage


@dataclass(frozen=True)
class SettingsDialogTheme:
    """配置编辑弹窗专属配置"""

    # 主体
    min_width: int = 800  # 最小宽度
    min_height: int = 300  # 最小高度
    margin: int = 0  # 通用间距
    desc_spacing: int = 4  # 控件与提示语间距

    # 标签页
    tab_min_width: int = 80  # 标签页标题最小宽度
    tab_padding_v: int = 6  # 标签页垂直内边距
    tab_padding_h: int = 16  # 标签页水平内边距
    tab_spacing: int = 12  # 标签页内部控件间距
    tab_bg: str = "#2D2D2D"  # 标签页背景色
    tab_container_name: str = (
        "settings_tab_container"  # 页容器样式名，改名同步 _parts 选择器
    )

    # 输入框
    input_padding_v: int = 6  # 输入框垂直内边距
    input_padding_h: int = 8  # 输入框水平内边距

    # 边框
    border_width: int = 1  # 边框宽度
    border_color: str = "#444444"  # 边框色

    # 按钮
    finish_btn_min_width: int = 150  # "完成"按钮最小宽度
    btn_min_width: int = 90  # 普通按钮最小宽度
    reset_btn_size: int = 26  # 恢复默认图标按钮边长
    reset_btn_font: int = 15  # 恢复默认图标字号
    btn_hover_bg: str = "#2B5A8A"  # 主按钮悬停背景色
    btn_pressed_bg: str = "#1A4060"  # 主按钮按下背景色

    # 勾选框
    check_size: int = 18  # 指示器边长，与 bootstrap PANEL.check_size 同步
    check_spacing: int = 6  # 指示器与文字间距

    # 人设预览
    persona_preview_height: int = 180  # 预览弹窗正文固定高度
    persona_preview_width: int = 520  # 预览弹窗正文固定宽度

    # 提示文案
    verified_ok: str = DialogMessage.SETUP_VERIFIED_OK
    history_reset: str = DialogMessage.SETUP_HISTORY_RESET

    # 按钮文案
    cancel_text: str = DialogMessage.BTN_CANCEL
    save_text: str = DialogMessage.BTN_SAVE
    exit_text: str = DialogMessage.BTN_EXIT
    finish_text: str = DialogMessage.BTN_FINISH
    validating_text: str = DialogMessage.BTN_VALIDATING
    reset_text: str = DialogMessage.SETUP_RESET
    reset_icon: str = DialogMessage.SETUP_RESET_ICON

    # 人设预览文案
    persona_title: str = DialogMessage.SETUP_PERSONA_TITLE
    persona_label: str = DialogMessage.SETUP_PERSONA_LABEL
    persona_preview_text: str = DialogMessage.SETUP_PERSONA_PREVIEW
    persona_apply_text: str = DialogMessage.PERSONA_APPLY
    persona_from_file: str = DialogMessage.SETUP_PERSONA_FROM_FILE
    persona_from_template: str = DialogMessage.SETUP_PERSONA_FROM_TEMPLATE
    persona_missing: str = DialogMessage.SETUP_PERSONA_MISSING
    persona_same: str = DialogMessage.SETUP_PERSONA_SAME
    persona_outdated: str = DialogMessage.SETUP_PERSONA_OUTDATED
    persona_edited: str = DialogMessage.SETUP_PERSONA_EDITED
    persona_unreadable: str = DialogMessage.SETUP_PERSONA_UNREADABLE
    persona_applied: str = DialogMessage.SETUP_PERSONA_APPLIED
    persona_pending: str = DialogMessage.SETUP_PERSONA_PENDING
    persona_file_create_fail: str = DialogMessage.SETUP_PERSONA_FILE_CREATE_FAIL
    persona_open_text: str = DialogMessage.SETUP_PERSONA_OPEN
    persona_open_fail: str = DialogMessage.SETUP_PERSONA_OPEN_FAIL
    persona_close_text: str = DialogMessage.SETUP_PERSONA_CLOSE

    # SETUP 提示文案
    setup_tip: str = DialogMessage.SETUP_TIP
    setup_hint: str = DialogMessage.SETUP_HINT

    # 窗口标题
    title: str = DialogMessage.SETUP_TITLE

    # 错误标注
    error_color: str = "#E06C75"
    pending_color: str = "#D7BA7D"  # 验证失败字段/标签页的标红色
    error_font_size: int = 11  # SETUP 提示语字号
    error_font_family: str = "Microsoft YaHei"  # SETUP 提示语字体


@dataclass(frozen=True)
class SettingsListTheme:
    """配置编辑列表项配置"""

    # 主按钮
    primary_bg = "#264F78"  # 背景色
    primary_hover_bg = "#3A6FA5"  # 悬停背景色
    primary_color = "#FFFFFF"  # 文字色

    # 次按钮
    secondary_color = "#AAAAAA"  # 文字色
    secondary_border_color = "#555555"  # 边框色
    secondary_hover_border_color = "#FF4D4F"  # 悬停边框色
    secondary_hover_color = "#FF4D4F"  # 悬停文字色
    secondary_hover_bg = "#2A0F10"  # 悬停背景色

    # 按钮尺寸
    btn_padding_h = 12  # 水平内边距
    btn_padding_v = 4  # 垂直内边距
    btn_min_width = 70  # 最小宽度

    # 列表项
    item_padding_v: int = 4  # 垂直内边距
    item_padding_h: int = 8  # 水平内边距
    item_border_width: int = 1  # 底部分割线宽度
    item_border_color: str = "#3C3C3C"  # 底部分割线颜色

    # 列表容器
    container_inner_margin = 2  # 内边距
    height: int = 90  # 列表区高度，可见约四行
