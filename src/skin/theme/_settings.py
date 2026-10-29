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
    persona_preview_width: int = 520  # 预览与编辑弹窗正文固定宽度
    persona_editor_height: int = 420  # 编辑弹窗正文固定高度
    persona_resolve_width: int = 900  # 拍板弹窗最小宽度，两栏并排
    persona_resolve_height: int = 460  # 拍板弹窗最小高度

    # 提示文案
    verified_ok: str = DialogMessage.SETUP_VERIFIED_OK
    history_reset: str = DialogMessage.SETUP_HISTORY_RESET

    # 按钮文案
    cancel_text: str = DialogMessage.BTN_CANCEL
    save_text: str = DialogMessage.BTN_SAVE
    confirm_text: str = DialogMessage.BTN_CONFIRM
    exit_text: str = DialogMessage.BTN_EXIT
    finish_text: str = DialogMessage.BTN_FINISH
    validating_text: str = DialogMessage.BTN_VALIDATING
    reset_text: str = DialogMessage.SETUP_RESET
    reset_icon: str = DialogMessage.SETUP_RESET_ICON

    # 人设正文文案
    persona_title: str = DialogMessage.SETUP_PERSONA_TITLE
    persona_label: str = DialogMessage.SETUP_PERSONA_LABEL
    persona_preview_text: str = DialogMessage.SETUP_PERSONA_PREVIEW
    persona_reload_text: str = DialogMessage.SETUP_PERSONA_RELOAD
    persona_reload_same: str = DialogMessage.SETUP_PERSONA_RELOAD_SAME
    persona_file_create_fail: str = DialogMessage.SETUP_PERSONA_FILE_CREATE_FAIL
    persona_file_read_fail: str = DialogMessage.SETUP_PERSONA_FILE_READ_FAIL
    persona_close_text: str = DialogMessage.SETUP_PERSONA_CLOSE
    persona_edit_text: str = DialogMessage.SETUP_PERSONA_EDIT
    persona_editor_title: str = DialogMessage.SETUP_PERSONA_EDITOR_TITLE
    persona_editor_tip: str = DialogMessage.SETUP_PERSONA_EDITOR_TIP
    persona_use_template: str = DialogMessage.SETUP_PERSONA_USE_TEMPLATE
    persona_no_template: str = DialogMessage.SETUP_PERSONA_NO_TEMPLATE
    persona_template_same: str = DialogMessage.SETUP_PERSONA_TEMPLATE_SAME

    # 人设拍板弹窗
    persona_resolve_title: str = DialogMessage.SETUP_PERSONA_RESOLVE_TITLE
    persona_resolve_text: str = DialogMessage.SETUP_PERSONA_RESOLVE_TEXT
    persona_resolve_use: str = DialogMessage.SETUP_PERSONA_RESOLVE_USE
    persona_resolve_back: str = DialogMessage.SETUP_PERSONA_RESOLVE_BACK
    persona_resolve_confirm: str = DialogMessage.SETUP_PERSONA_RESOLVE_CONFIRM
    persona_resolve_confirm_text: str = DialogMessage.SETUP_PERSONA_RESOLVE_CONFIRM_TEXT
    persona_resolve_same: str = DialogMessage.SETUP_PERSONA_RESOLVE_SAME

    # 人设栏名与来源词
    persona_label_saved: str = DialogMessage.SETUP_PERSONA_LABEL_SAVED
    persona_label_active: str = DialogMessage.SETUP_PERSONA_LABEL_ACTIVE
    persona_label_file: str = DialogMessage.SETUP_PERSONA_LABEL_FILE
    persona_label_disk: str = DialogMessage.SETUP_PERSONA_LABEL_DISK
    persona_label_edited: str = DialogMessage.SETUP_PERSONA_LABEL_EDITED
    persona_label_template: str = DialogMessage.SETUP_PERSONA_LABEL_TEMPLATE
    persona_source_file: str = DialogMessage.SETUP_PERSONA_SOURCE_FILE
    persona_source_panel: str = DialogMessage.SETUP_PERSONA_SOURCE_PANEL
    persona_source_template: str = DialogMessage.SETUP_PERSONA_SOURCE_TEMPLATE

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
