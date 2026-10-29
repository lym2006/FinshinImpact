# src/skin/theme/_dialogs.py
"""弹窗令牌

- 定义通知类弹窗的尺寸、文案与配色
- 弹窗话术字段一律代理引用 messages
- 诊断窗与校验窗共用五态基类，同款渲染令牌一处一源
"""

from dataclasses import dataclass

from ..messages import CheckMessage, DialogMessage, MiscMessage, VersionMessage

# 五态渲染色：诊断窗与校验窗同款（一处一源）
_PENDING_COLOR = "#808080"  # 等待检测
_CHECKING_COLOR = "#FFFFFF"  # 正在检测
_OK_COLOR = "#4EC97B"  # 正常
_SKIP_COLOR = "#4EC97B"  # 前级已连通，同样绿显
_FAIL_COLOR = "#F44E4E"  # 异常


@dataclass(frozen=True)
class ShutdownDialogTheme:
    """退出拦截弹窗专属配置"""

    # 尺寸配置
    width: int = 400  # 宽度
    height: int = 160  # 高度
    padding: int = 30  # 内边距
    spacing: int = 20  # 元素间距

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
class FiveStateDialogTheme:
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
class CheckDialogTheme(FiveStateDialogTheme):
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
class WaitDialogTheme:
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
class NoticeDialogTheme:
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

    # 人设对账弹窗文案
    persona_title: str = DialogMessage.NOTICE_TITLE
    persona_text: str = MiscMessage.PERSONA_OUTDATED
    persona_apply_text: str = DialogMessage.PERSONA_APPLY
    persona_keep_text: str = DialogMessage.PERSONA_KEEP
    persona_applied: str = MiscMessage.PERSONA_APPLIED
    persona_apply_fail: str = MiscMessage.PERSONA_APPLY_FAIL


@dataclass(frozen=True)
class ReleaseNotesDialogTheme:
    """版本变化弹窗专属配置

    - 左列版本清单，右侧正文走只读文本框，超出高度由滚动条接住
    """

    # 尺寸配置
    width: int = 880
    height: int = 520
    pad: int = 24
    spacing: int = 14
    list_width: int = 170

    # 文案配置
    title: str = DialogMessage.RELEASE_NOTES_TITLE
    loading: str = DialogMessage.RELEASE_NOTES_LOADING
    ready: str = DialogMessage.RELEASE_NOTES_READY
    ok_text: str = DialogMessage.NOTICE_OK


@dataclass(frozen=True)
class LinkDialogTheme:
    """断连计时弹窗专属配置"""

    # 尺寸配置
    width: int = 340
    height: int = 170
    pad: int = 24
    spacing: int = 12

    # 字体配置
    font_name: str = "Microsoft YaHei"  # 字体家族名
    head_font_size: int = 13  # 提示行字号
    retries_font_size: int = 12  # 重试次数行字号
    timer_font_size: int = 26  # 计时行字号

    # 文案配置
    title: str = DialogMessage.LINK_TITLE
    head: str = DialogMessage.LINK_HEAD
    elapsed_fmt: str = DialogMessage.LINK_ELAPSED
    retries_fmt: str = DialogMessage.LINK_RETRIES
    mute_text: str = DialogMessage.LINK_MUTE

    # 颜色配置
    bg_color: str = "#2b2b2b"  # 弹窗背景色
    text_color: str = "#ffffff"  # 提示文字颜色
    timer_color: str = _FAIL_COLOR  # 计时行红显
    mute_bg: str = "#3c3c3c"  # 静默按钮背景
    btn_color: str = "#ffffff"  # 按钮文字色


@dataclass(frozen=True)
class ChangeDialogTheme:
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
    diff_skip: str = "#8C8C8C"  # 折叠提示行与对侧占位行文字色
