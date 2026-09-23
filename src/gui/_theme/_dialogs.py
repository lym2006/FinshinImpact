# src/gui/_theme/_dialogs.py
"""弹窗令牌（内部实现）

- 定义各专属弹窗的尺寸、文案与配色
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SettingsDialogConfig:
    """配置编辑弹窗专属配置"""

    # === 主体 ===
    min_width: int = 800  # 最小宽度
    min_height: int = 300  # 最小高度
    margin: int = 0  # 通用间距
    desc_spacing: int = 4  # 控件与提示语间距

    # === 标签页 ===
    tab_min_width: int = 80  # 标签页标题最小宽度
    tab_padding_v: int = 6  # 标签页垂直内边距
    tab_padding_h: int = 16  # 标签页水平内边距
    tab_spacing: int = 12  # 标签页内部控件间距
    tab_bg: str = "#2D2D2D"  # 标签页背景色

    # === 输入框 ===
    input_padding_v: int = 6  # 输入框垂直内边距
    input_padding_h: int = 8  # 输入框水平内边距

    # === 边框 ===
    border_width: int = 1  # 边框宽度
    border_color: str = "#444444"  # 边框色

    # === 按钮 ===
    finish_btn_min_width: int = 150  # "完成"按钮最小宽度
    btn_min_width: int = 90  # 普通按钮最小宽度
    btn_hover_bg: str = "#2B5A8A"  # 主按钮悬停背景色
    btn_pressed_bg: str = "#1A4060"  # 主按钮按下背景色

    # === 勾选框 ===
    check_size: int = 14  # 指示器边长
    check_spacing: int = 6  # 指示器与文字间距

    # === 提示文案 ===
    verified_ok: str = "无改动，连通性验证通过"

    # === 按钮文案 ===
    cancel_text: str = "取消"
    save_text: str = "保存"
    exit_text: str = "退出程序"
    finish_text: str = "完成并保存"
    validating_text: str = "校验中..."

    # === SETUP 提示文案 ===
    setup_tip: str = "检测到配置有误，请修正后继续"
    setup_hint: str = "留意带 ⚠ 的标签页，标题标红的即为出错字段"

    # === 窗口标题 ===
    title: str = "修改配置"

    # === 错误标注 ===
    error_color: str = "#E06C75"
    pending_color: str = "#D7BA7D"  # 验证失败字段/标签页的标红色
    error_font_size: int = 11  # SETUP 提示语字号
    error_font_family: str = "Microsoft YaHei"  # SETUP 提示语字体


@dataclass(frozen=True)
class SettingsListConfig:
    """配置编辑列表项配置"""

    # === 主按钮 ===
    primary_bg = "#264F78"  # 背景色
    primary_hover_bg = "#3A6FA5"  # 悬停背景色
    primary_color = "#FFFFFF"  # 文字色

    # === 次按钮 ===
    secondary_color = "#AAAAAA"  # 文字色
    secondary_border_color = "#555555"  # 边框色
    secondary_hover_border_color = "#FF4D4F"  # 悬停边框色
    secondary_hover_color = "#FF4D4F"  # 悬停文字色
    secondary_hover_bg = "#2A0F10"  # 悬停背景色

    # === 按钮尺寸 ===
    btn_padding_h = 12  # 水平内边距
    btn_padding_v = 4  # 垂直内边距
    btn_min_width = 70  # 最小宽度

    # === 列表项 ===
    item_padding_v: int = 4  # 垂直内边距
    item_padding_h: int = 8  # 水平内边距
    item_border_width: int = 1  # 底部分割线宽度
    item_border_color: str = "#3C3C3C"  # 底部分割线颜色

    # === 列表容器 ===
    container_inner_margin = 2  # 内边距


@dataclass(frozen=True)
class ShutdownDialogConfig:
    """退出拦截弹窗专属配置"""

    # === 尺寸配置 ===
    width: int = 400  # 宽度
    height: int = 160  # 高度
    padding: int = 30  # 内边距
    spacing: int = 20  # 元素间距
    btn_width: int = 100  # 按钮宽度
    btn_height: int = 35  # 按钮高度

    # === 字体配置 ===
    font_name: str = "Microsoft YaHei"  # 字体家族名
    font_size: int = 14  # 弹窗字号

    # === 文案配置 ===
    title: str = "确认退出"
    message: str = "确定要关闭机器人并退出程序吗？"
    cancel_text: str = "取消"
    confirm_text: str = "确认"

    # === 颜色配置 ===
    bg_color: str = "#2b2b2b"  # 弹窗背景色
    text_color: str = "#ffffff"  # 提示文字颜色
    cancel_bg: str = "#555555"  # 取消按钮背景
    cancel_color: str = "#ffffff"  # 取消按钮文字
    confirm_bg: str = "#d32f2f"  # 确认按钮背景（警告红）
    confirm_color: str = "#ffffff"  # 确认按钮文字


@dataclass(frozen=True)
class FatalDialogConfig:
    """致命错误弹窗专属配置"""

    # === 尺寸配置 ===
    width: int = 420  # 宽度
    height: int = 180  # 高度
    padding: int = 20  # 内边距
    spacing: int = 12  # 元素间距

    # === 文案配置 ===
    title: str = "程序遇到无法恢复的错误，即将退出"
    confirm_text: str = "确认并退出"


@dataclass(frozen=True)
class ProxyDialogConfig:
    """网络诊断弹窗专属配置"""

    # === 尺寸配置 ===
    width: int = 460
    height: int = 320
    pad: int = 16
    row_margin: int = 4  # HTML 行距

    # === 文案配置 ===
    title: str = "网络诊断"
    btn_text: str = "开始诊断"
    running_text: str = "诊断中..."
    retry_text: str = "重新检测"
    pending_mark: str = "•"
    checking_mark: str = "…"
    ok_mark: str = "✓"
    fail_mark: str = "✗"

    # === 状态颜色 ===
    pending_color: str = "#808080"  # 等待检测
    checking_color: str = "#FFFFFF"  # 正在检测
    ok_color: str = "#4EC97B"  # 正常
    fail_color: str = "#F44E4E"  # 异常
    section_color: str = "#569CD6"  # 分组标题


@dataclass(frozen=True)
class WaitDialogConfig:
    """忙碌等待弹窗专属配置"""

    # === 尺寸配置 ===
    width: int = 360
    height: int = 200
    pad: int = 24
    spinner_font_size: int = 26

    # === 动画配置 ===
    spinner_frames: str = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    tick_ms: int = 120

    # === 文案配置 ===
    title: str = "请稍候"
    ok_text: str = "知道了"
    check_text: str = "正在检查版本更新..."
    verify_text: str = "正在校验连通性..."
    verify_format: str = "正在校验连通性... 已等 {n} 秒"
    verified: str = "连通性校验通过"
    up_to_date: str = "已是最新版本：{ver}"
    crash_text: str = "检查异常中断，详情见日志"

    # === 颜色与符号 ===
    spinner_color: str = "#569CD6"
    ok_mark: str = "✓"
    fail_mark: str = "✗"


@dataclass(frozen=True)
class HintDialogConfig:
    """通用提示弹窗专属配置"""

    # === 尺寸配置 ===
    width: int = 380
    height: int = 150
    pad: int = 24
    spacing: int = 14

    # === 文案配置 ===
    title: str = "提示"
    ok_text: str = "知道了"
    not_changed: str = "您未修改任何配置"


@dataclass(frozen=True)
class ChangeDialogConfig:
    """配置变更二次确认弹窗专属配置"""

    # === 尺寸配置 ===
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

    # === 文案配置 ===
    title: str = "确认变更"
    diff_columns: int = 3  # 配置项/原配置/新配置三列
    tip_text: str = "以下配置将被修改，确认保存？"
    col_key: str = "配置项"
    col_ori: str = "原配置"
    col_mod: str = "新配置"
    cancel_text: str = "返回修改"
    confirm_text: str = "确认保存"

    # === 颜色配置 ===
    grid_color: str = "#3C3C3C"  # 表格分割线
    alt_bg: str = "#252526"  # 隔行背景
    diff_del: str = "#F44E4E"  # 删除行红色（带删除线）
    diff_add: str = "#4EC97B"  # 新增行绿色加粗
