# src/gui/_theme/_dialogs.py
"""弹窗令牌

- 定义各专属弹窗的尺寸、文案与配色
- 弹窗话术字段一律代理引用 messages，令牌不持有话术字面量
- 诊断窗与校验窗共用五态基类，同款渲染令牌一处一源
"""

from dataclasses import dataclass

from messages import CheckMessage, DialogMessage, VersionMessage

# 五态渲染色：诊断窗与校验窗同款（一处一源）
_PENDING_COLOR = "#808080"  # 等待检测
_CHECKING_COLOR = "#FFFFFF"  # 正在检测
_OK_COLOR = "#4EC97B"  # 正常
_SKIP_COLOR = "#4EC97B"  # 前级已连通，同样绿显
_FAIL_COLOR = "#F44E4E"  # 异常


@dataclass(frozen=True)
class SettingsDialogConfig:
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
    tab_container_name: str = "settings_tab_container"  # 页容器样式名，改名同步 _parts 选择器

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
    check_size: int = 14  # 指示器边长
    check_spacing: int = 6  # 指示器与文字间距

    # 人设预览
    persona_preview_height: int = 180  # 预览弹窗正文固定高度
    persona_preview_width: int = 520  # 预览弹窗正文固定宽度

    # 提示文案
    verified_ok: str = DialogMessage.SETUP_VERIFIED_OK

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
    persona_preview_text: str = DialogMessage.SETUP_PERSONA_PREVIEW
    persona_from_file: str = DialogMessage.SETUP_PERSONA_FROM_FILE
    persona_from_config: str = DialogMessage.SETUP_PERSONA_FROM_CONFIG
    persona_missing: str = DialogMessage.SETUP_PERSONA_MISSING
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
class SettingsListConfig:
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


@dataclass(frozen=True)
class ShutdownDialogConfig:
    """退出拦截弹窗专属配置"""

    # 尺寸配置
    width: int = 400  # 宽度
    height: int = 160  # 高度
    padding: int = 30  # 内边距
    spacing: int = 20  # 元素间距
    btn_width: int = 100  # 按钮宽度
    btn_height: int = 35  # 按钮高度

    # 字体配置
    font_name: str = "Microsoft YaHei"  # 字体家族名
    font_size: int = 14  # 弹窗字号

    # 文案配置
    title: str = DialogMessage.SHUTDOWN_TITLE
    message: str = DialogMessage.SHUTDOWN_MSG
    cancel_text: str = DialogMessage.BTN_CANCEL
    confirm_text: str = DialogMessage.BTN_CONFIRM

    # 颜色配置
    bg_color: str = "#2b2b2b"  # 弹窗背景色
    text_color: str = "#ffffff"  # 提示文字颜色
    cancel_bg: str = "#555555"  # 取消按钮背景
    cancel_color: str = "#ffffff"  # 取消按钮文字
    confirm_bg: str = "#d32f2f"  # 确认按钮背景（警告红）
    confirm_color: str = "#ffffff"  # 确认按钮文字


@dataclass(frozen=True)
class FiveStateDialogConfig:
    """五态行表格弹窗共用配置

    - 诊断窗与校验窗同款表格、同款符号与颜色，渲染令牌收在基类一处
    """

    # 尺寸配置
    width: int = 520
    pad: int = 16
    row_margin: int = 4  # HTML 行距

    # 进行中行计时
    countdown: str = CheckMessage.COUNTDOWN

    # 五态符号
    pending_mark: str = DialogMessage.MARK_PENDING
    checking_mark: str = DialogMessage.MARK_CHECKING
    ok_mark: str = DialogMessage.MARK_OK
    skip_mark: str = DialogMessage.MARK_SKIP
    fail_mark: str = DialogMessage.MARK_FAIL

    # 五态颜色
    pending_color: str = _PENDING_COLOR
    checking_color: str = _CHECKING_COLOR
    ok_color: str = _OK_COLOR
    skip_color: str = _SKIP_COLOR
    fail_color: str = _FAIL_COLOR


@dataclass(frozen=True)
class CheckDialogConfig(FiveStateDialogConfig):
    """检查进度窗专属配置

    - 校验轮与诊断轮共用同一实例
    """

    # 动画配置
    spinner_frames: str = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    tick_ms: int = 120

    # 共用文案
    ok_text: str = DialogMessage.NOTICE_OK
    cancel_text: str = DialogMessage.BTN_CANCEL

    # 校验轮文案
    verify_title: str = DialogMessage.CHECK_VERIFY_TITLE
    verify_head: str = DialogMessage.CHECK_VERIFY_HEAD
    verify_head_pass: str = DialogMessage.CHECK_VERIFY_HEAD_PASS
    verify_head_fail: str = DialogMessage.CHECK_VERIFY_HEAD_FAIL

    # 诊断轮文案
    diagnose_title: str = DialogMessage.CHECK_DIAG_TITLE
    diagnose_head: str = DialogMessage.CHECK_DIAG_HEAD
    diagnose_head_pass: str = DialogMessage.CHECK_DIAG_HEAD_PASS
    diagnose_head_fail: str = DialogMessage.CHECK_DIAG_HEAD_FAIL


@dataclass(frozen=True)
class WaitDialogConfig:
    """忙碌等待弹窗专属配置"""

    # 尺寸配置
    width: int = 360
    height: int = 200
    pad: int = 24
    spinner_font_size: int = 26
    line_height: int = 24  # 多行结果的每行高度

    # 动画配置
    spinner_frames: str = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    tick_ms: int = 120

    # 文案配置
    title: str = DialogMessage.WAIT_TITLE
    ok_text: str = DialogMessage.NOTICE_OK
    cancel_text: str = DialogMessage.BTN_CANCEL
    check_text: str = DialogMessage.WAIT_CHECK
    up_to_date: str = VersionMessage.UP_TO_DATE
    crash_text: str = VersionMessage.CRASH

    # 颜色与符号
    spinner_color: str = "#569CD6"
    ok_mark: str = "✓"
    fail_mark: str = "✗"


@dataclass(frozen=True)
class NoticeDialogConfig:
    """通知弹窗专属配置

    - 提示/致命共用，critical 区分
    """

    # 尺寸配置
    width: int = 420
    height: int = 150
    pad: int = 24
    spacing: int = 14

    # 文案配置
    title: str = DialogMessage.NOTICE_TITLE
    ok_text: str = DialogMessage.NOTICE_OK
    fatal_title: str = DialogMessage.NOTICE_FATAL_TITLE
    fatal_head: str = DialogMessage.NOTICE_FATAL_HEAD
    fatal_ok: str = DialogMessage.NOTICE_FATAL_OK
    not_changed: str = DialogMessage.NOTICE_NOT_CHANGED


@dataclass(frozen=True)
class ChangeDialogConfig:
    """配置变更二次确认弹窗专属配置"""

    # 尺寸配置
    min_width: int = 560  # 最小宽度
    min_height: int = 280  # 最小高度
    row_height: int = 28  # 表格行高（防内容换行挤压）
    row_min_lines: int = 2  # 单元格最小显示行数
    row_max_lines: int = 6  # 单元格最大显示行数，超出内部滚动
    row_pad: int = 24  # 行高额外留白（含横向滚动条占位）
    cell_padding_v: int = 2  # diff 单元格内边距（纵向）
    cell_padding_h: int = 4  # diff 单元格内边距（横向）
    mono_family: str = "Consolas"  # 取值列等宽字体
    mono_font_size: int = 9  # 取值列字号

    # 文案配置
    title: str = DialogMessage.CHANGE_TITLE
    diff_columns: int = 3  # 配置项/原配置/新配置三列
    tip_text: str = DialogMessage.CHANGE_TIP
    col_key: str = DialogMessage.CHANGE_COL_KEY
    col_ori: str = DialogMessage.CHANGE_COL_ORI
    col_mod: str = DialogMessage.CHANGE_COL_MOD
    cancel_text: str = DialogMessage.CHANGE_RETURN
    confirm_text: str = DialogMessage.CHANGE_CONFIRM

    # 颜色配置
    grid_color: str = "#3C3C3C"  # 表格分割线
    alt_bg: str = "#252526"  # 隔行背景
    diff_del: str = _FAIL_COLOR  # 删除行红色（带删除线）
    diff_add: str = _OK_COLOR  # 新增行绿色加粗
