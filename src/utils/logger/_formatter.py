# src/utils/logger/_formatter.py
"""日志格式器（内部实现）

- 定义统一格式与语义标记规则
- 实现仪表盘日志按语义注入标记
"""

import logging

# ==================== 格式模板 ====================

_FMT = "%(asctime)s | %(name)-20s | %(levelname)-5s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

# ==================== 结果标记（只看冒号前的头部文字） ====================

_MARK_CANCEL = "\U0001f6ab"  # 🚫 取消
_MARK_PAUSE = "\u23f8\ufe0f"  # ⏸️ 中断
_MARK_WARN = "\u26a0\ufe0f"  # ⚠️ 软警告
_MARK_ERR = "\u274c"  # ❌ 错误
_MARK_OK = "\u2705"  # ✅ 成功
_MARK_STOP = "\U0001f6d1"  # 🛑 停止
_MARK_HINT = "\U0001f4a1"  # 💡 检测提示
_MARK_DEFAULT = "\u2139\ufe0f"  # ℹ️ 兜底

# 词表保持最小集，靠文案标准化命中；error 级未命中词汇时默认 ❌
_RESULT_RULES = (
    (_MARK_CANCEL, ("取消",)),
    (_MARK_PAUSE, ("中断", "被删除")),
    (_MARK_WARN, ("未检测", "未修改", "重连", "重试", "频控")),
    (_MARK_ERR, ("失败", "错误", "异常")),
    (_MARK_OK, ("成功", "完成", "通过")),
    (_MARK_STOP, ("停止", "退出")),
    (_MARK_HINT, ("检测到", "发现")),
)

# ==================== 领域标记（无结果语义的过程行） ====================

_DOMAIN_RULES = (
    ("\U0001f4e5", ("入队",)),  # 📥
    ("\U0001f4ac", ("私聊", "群组", "超级群", "频道", "对话")),  # 💬
    ("\U0001f5bc\ufe0f", ("截图", "图片")),  # 🖼️
    ("\U0001f310", ("浏览器",)),  # 🌐
    ("\U0001f5a5\ufe0f", ("监控",)),  # 🖥️
    ("\U0001f4c2", ("路径", "目录")),  # 📂
    ("\U0001f50d", ("检查", "扫描", "版本")),  # 🔍
    ("\u23f3", ("等待",)),  # ⏳
    ("\U0001f9f9", ("清理",)),  # 🧹
    ("\U0001f916", ("引擎", "轮询")),  # 🤖
    ("\U0001f50c", ("插件",)),  # 🔌
    ("\U0001f4be", ("保存", "写入", "磁盘")),  # 💾
    ("\u2699\ufe0f", ("配置", "校验", "验证", "加载")),  # ⚙️
    ("\U0001f4c3", ("日志", "文件")),  # 📃
)


def _resolve_mark(levelno: int, text: str) -> str:
    """解析日志标记

    只看冒号前的头部，防后文误伤；未命中时 error 级红叉、其余图标、ℹ️ 兜底
    """
    head = text.split("：", 1)[0].split(":", 1)[0]

    for mark, words in _RESULT_RULES:
        if any(w in head for w in words):
            return mark
    if levelno >= logging.ERROR:
        return _MARK_ERR
    for mark, words in _DOMAIN_RULES:
        if any(w in head for w in words):
            return mark
    return _MARK_DEFAULT


class MarkedFormatter(logging.Formatter):
    """在标准格式之上按语义注入状态标记前缀"""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        parts = base.split(" | ", 3)  # 消息内可含 |，只切前三个分隔符
        if len(parts) < 4:
            return base
        prefix, message = " | ".join(parts[:3]), parts[3]
        mark = _resolve_mark(record.levelno, message)
        return f"{prefix} | {mark} {message}"


def create_formatter(marked: bool = False) -> logging.Formatter:
    """创建日志格式器"""
    cls = MarkedFormatter if marked else logging.Formatter
    return cls(fmt=_FMT, datefmt=_DATEFMT)
