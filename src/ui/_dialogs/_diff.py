# src/ui/_dialogs/_diff.py
"""变更 diff 渲染

- 实现配置值的行级与字符级比对
- 两栏补位与未改动折叠供长文比对
- 提供只读 diff 单元格构建
"""

import difflib
import html

from PySide6.QtWidgets import QTextEdit

from skin.theme import CHANGE_DIALOG, ObjectName

_DIFF_STYLE = {
    "same": "",
    "del": f"color: {CHANGE_DIALOG.diff_del}; text-decoration: line-through;",
    "add": f"color: {CHANGE_DIALOG.diff_add}; font-weight: bold;",
    "skip": f"color: {CHANGE_DIALOG.diff_skip};",
    "blank": f"color: {CHANGE_DIALOG.diff_skip};",
}

# 一行内的 (类型, 文本) 分段序列
_Line = list[tuple[str, str]]

# 对侧无同行时的占位符，只为把行撑住
_BLANK_MARK = "⋮"

# 未改动段省不到这么多行就不折，提示行本身要占一行
_MIN_OMITTED = 4


def to_lines(value: object) -> list[str]:
    """配置值拆行

    - list 逐元素，标量按文本行
    """
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    return str(value).splitlines() or [""]


def _char_diff(old: str, new: str) -> tuple[_Line, _Line]:
    """行内字符级比对

    - 旧/新各输出 (类型, 文本) 分段
    """
    # 公共部分白色
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
    """行级对齐并做配对行字符级比对

    - 修改行只高亮改动处
    - 增删行整行标记，另一栏不补位
    """
    return _diff_rows(old, new, pad=False, context=None, skip_text="")


def split_diff_aligned(
    old: list[str],
    new: list[str],
    skip_text: str,
    context: int | None,
) -> tuple[list[_Line], list[_Line]]:
    """两栏逐行等高的比对，长段未改动折成一行提示

    - 增删行在另一栏补占位行，同一行落在同一高度
    - context 给 None 即整份铺开，一行也不折
    """
    return _diff_rows(old, new, pad=True, context=context, skip_text=skip_text)


def _diff_rows(
    old: list[str],
    new: list[str],
    *,
    pad: bool,
    context: int | None,
    skip_text: str,
) -> tuple[list[_Line], list[_Line]]:
    """按 opcode 铺两栏，pad 与 context 分别管补位与折叠"""
    sm = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    left: list[_Line] = []
    right: list[_Line] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            _emit_equal(left, right, old, i1, i2, context, skip_text)
        else:
            _emit_change(left, right, old, new, tag, i1, i2, j1, j2, pad)
    return left, right


def _emit_equal(
    left: list[_Line],
    right: list[_Line],
    old: list[str],
    i1: int,
    i2: int,
    context: int | None,
    skip_text: str,
) -> None:
    """未改动段入两栏，够长即折成头尾各留 context 行"""
    rows = old[i1:i2]
    if context is not None:
        omitted = len(rows) - context * 2
        if omitted >= _MIN_OMITTED:
            _emit_fold(left, right, rows, context, omitted, skip_text)
            return
    left += _same_rows(rows)
    right += _same_rows(rows)


def _emit_fold(
    left: list[_Line],
    right: list[_Line],
    rows: list[str],
    context: int,
    omitted: int,
    skip_text: str,
) -> None:
    """头尾各留 context 行，中间换成一行省略提示"""
    head, tail = rows[:context], rows[-context:]
    hint = skip_text.format(n=omitted)
    for side in (left, right):
        side += _same_rows(head)
        side.append([("skip", hint)])
        side += _same_rows(tail)


def _same_rows(lines: list[str]) -> list[_Line]:
    """整段未改动的行，两栏各取一份"""
    return [[("same", line)] for line in lines]


def _emit_change(
    left: list[_Line],
    right: list[_Line],
    old: list[str],
    new: list[str],
    tag: str,
    i1: int,
    i2: int,
    j1: int,
    j2: int,
    pad: bool,
) -> None:
    """增删与替换行入栏，pad 为真时给对侧补等长占位"""
    if tag == "delete":
        removed = [[("del", line)] for line in old[i1:i2]]
        left += removed
        right += _blanks(len(removed)) if pad else []
    elif tag == "insert":
        added = [[("add", line)] for line in new[j1:j2]]
        right += added
        left += _blanks(len(added)) if pad else []
    else:  # replace：等长部分逐行字符级，多余部分整行
        old_lines, new_lines = old[i1:i2], new[j1:j2]
        pairs = min(len(old_lines), len(new_lines))
        for a, b in zip(old_lines[:pairs], new_lines[:pairs], strict=False):
            la, rb = _char_diff(a, b)
            left.append(la)
            right.append(rb)
        surplus_old = [[("del", line)] for line in old_lines[pairs:]]
        surplus_new = [[("add", line)] for line in new_lines[pairs:]]
        left += surplus_old
        right += surplus_new
        if pad:
            right += _blanks(len(surplus_old))
            left += _blanks(len(surplus_new))


def _blanks(count: int) -> list[_Line]:
    """对侧占位行，只撑高度不带内容"""
    return [[("blank", _BLANK_MARK)] for _ in range(count)]


def diff_html(lines: list[_Line], mono: str) -> str:
    """一栏正文的 HTML，一行一个 div"""
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
    return f"<div style=\"font-family: '{mono}';\">{body}</div>"


def make_diff_cell(lines: list[_Line], mono: str) -> QTextEdit:
    """只读 diff 单元格

    - 超行高自动出滚动条
    """
    view = QTextEdit()
    view.setObjectName(ObjectName.CHANGE_CELL)
    view.setReadOnly(True)
    view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
    view.setHtml(diff_html(lines, mono))
    return view
