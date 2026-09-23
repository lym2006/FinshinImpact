# src/gui/dialogs/_settings/_diff.py
"""变更 diff 渲染（内部实现）

- 实现配置值的行级与字符级比对
- 提供只读 diff 单元格构建
"""

import difflib
import html

from PySide6.QtWidgets import QTextEdit

from ..._theme import CHANGE_DIALOG as CHANGE

_DIFF_STYLE = {
    "same": "",
    "del": f"color: {CHANGE.diff_del}; text-decoration: line-through;",
    "add": f"color: {CHANGE.diff_add}; font-weight: bold;",
}

# 一行内的 (类型, 文本) 分段序列
_Line = list[tuple[str, str]]


def to_lines(value: object) -> list[str]:
    """配置值拆行

    list 逐元素，标量按文本行。
    """
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    return str(value).splitlines() or [""]


def _char_diff(old: str, new: str) -> tuple[_Line, _Line]:
    """行内字符级比对

    旧/新各输出 (类型, 文本) 分段，公共部分白色。
    """
    sm = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    left: _Line = []
    right: _Line = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            left.append(("same", old[i1:i2]))
            right.append(("same", new[j1:j2]))
        else:
            if old[i1:i2]:
                left.append(("del", old[i1:i2]))
            if new[j1:j2]:
                right.append(("add", new[j1:j2]))
    return left, right


def split_diff(old: list[str], new: list[str]) -> tuple[list[_Line], list[_Line]]:
    """行级对齐 + 配对行字符级细化

    改词只亮改动处，多出的行整行删除/新增。
    """
    sm = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    left: list[_Line] = []
    right: list[_Line] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            lines = old[i1:i2]
            left += [[("same", ln)] for ln in lines]
            right += [[("same", ln)] for ln in lines]
        elif tag == "delete":
            left += [[("del", ln)] for ln in old[i1:i2]]
        elif tag == "insert":
            right += [[("add", ln)] for ln in new[j1:j2]]
        else:  # replace：等长部分逐行字符级，多余部分整行
            old_lines, new_lines = old[i1:i2], new[j1:j2]
            pairs = min(len(old_lines), len(new_lines))
            for a, b in zip(old_lines[:pairs], new_lines[:pairs], strict=False):
                la, rb = _char_diff(a, b)
                left.append(la)
                right.append(rb)
            left += [[("del", ln)] for ln in old_lines[pairs:]]
            right += [[("add", ln)] for ln in new_lines[pairs:]]
    return left, right


def make_diff_cell(lines: list[_Line], mono: str) -> QTextEdit:
    """只读 diff 单元格

    超行高自动出滚动条。
    """
    body = (
        "".join(
            "<div>"
            + (
                "".join(
                    f"<span style='{_DIFF_STYLE[kind]}'>"
                    f"{html.escape(text) or '&nbsp;'}</span>"
                    for kind, text in seg
                )
                or "&nbsp;"
            )
            + "</div>"
            for seg in lines
        )
        or "&nbsp;"
    )
    view = QTextEdit()
    view.setObjectName("change_cell")
    view.setReadOnly(True)
    view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
    view.setHtml(f"<div style=\"font-family: '{mono}';\">{body}</div>")
    return view
