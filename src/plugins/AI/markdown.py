# src/plugins/AI/markdown.py
"""模型应答纯文本清洗

- 剥掉星号、下划线、反引号、井号与链接标记，正文一字不动
- 围栏代码只去围栏行，保留行间正文
"""

import re

# 围栏行：``` 或 ~~~ 起头的整行连同换行丢弃，行间正文保留
_FENCE_RE = re.compile(r"(?m)^[ \t]*(?:`{3,}|~{3,}|={3,}|#{3,})[^\n]*\n?")

# 图片整体删除，链接只留标签文字
_IMAGE_RE = re.compile(r"!\[[^\]\n]*\]\([^)\n]*\)")
_LINK_RE = re.compile(r"\[([^\]\n]*)\]\([^)\n]*\)")

# 标题行：行首 # 串连同后随空格去掉
_HEADING_RE = re.compile(r"(?m)^[ \t]*#{1,6}[ \t]+")

# 行内代码：内容允许空格与星号残留，限在一行内
_CODE_RE = re.compile(r"`{1,3}([^`\n]{1,200}?)`{1,3}")

# 成对强调：内容与两侧标记字符互斥防嵌套吞并，带空格的 `* 乘号 *` 不误伤
_EMPH_RE = re.compile(r"(\*{2,3}|_{2,3}|~~)([^*_~`\s]{1,120}?)\1")

# 单词式斜体：内容与两侧星号紧贴，跳过成对强调后剩的单星号在这里收掉
_ITALIC_RE = re.compile(r"(?<!\*)\*(?![\s*])([^*\s`]{1,120}?)(?<!\s)\*(?!\*)")

# 成对标记替换后可能露出下一层，循环到剥不动为止
# (正则, 替换)：替换为组号即只留捕获内容，None 即整段删除
_PAIR_PATTERNS: tuple[tuple[re.Pattern[str], int | None], ...] = (
    (_FENCE_RE, None),
    (_IMAGE_RE, None),
    (_LINK_RE, 1),
    (_CODE_RE, 1),
    (_EMPH_RE, 2),
    (_ITALIC_RE, 1),
)


def strip_model_marks(text: str) -> str:
    """把模型给的样式标记洗成纯文本

    - 人设已禁样式，此处是漏网兜底
    - 只去标记符号，正文与换行原样保留
    """
    cleaned = text
    changed = True
    while changed:
        before = cleaned
        cleaned = _HEADING_RE.sub("", cleaned)
        for pattern, repl in _PAIR_PATTERNS:
            cleaned = pattern.sub(lambda m, r=repl: "" if r is None else m[r], cleaned)
        changed = cleaned != before
    return cleaned
