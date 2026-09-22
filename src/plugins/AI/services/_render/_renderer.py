# src/plugins/AI/services/_render/_renderer.py
"""渲染核心（内部实现）

- 实现 Markdown 转 HTML 与清洗
- 提供 Prism 高亮脚本注入
"""

import re

import bleach
from markdown import markdown as md

from ._css import ALLOWED_ATTRS, ALLOWED_TAGS, CDN_BASE, HEAD, PRISM_COMPONENTS, TAIL

# ==================== Markdown 转 HTML ====================


def _generate_html(text: str) -> str:
    """组装完整 HTML 文档"""
    html_body = md(
        text,
        extensions=["fenced_code", "tables", "nl2br", "codehilite"],
        extension_configs={
            "codehilite": {
                "linenums": False,
                "use_pygments": False,
                "lang_prefix": "language-",
            }
        },
    )

    # XSS 防御，清洗 HTML，只放行安全标签和属性
    html_body = bleach.clean(html_body, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)

    return html_body


# ==================== Prism 脚本注入 ====================


def _build_prism_scripts(langs_found: set[str]) -> str:
    """构建高亮脚本标签"""
    # 未检测到代码时返回空串
    # 提取所有代码块的语言标识
    if not langs_found:
        return ""
    scripts = [
        '\n<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>'
    ]

    for lang in langs_found:
        if (lang_key := lang.lower()) in PRISM_COMPONENTS:
            js_file = PRISM_COMPONENTS[lang_key]
            scripts.append(f'<script src="{CDN_BASE}{js_file}"></script>')

    return "\n".join(scripts)


# ==================== 渲染主入口 ====================


def render_html(text: str) -> str:
    """渲染完整 HTML 页面

    MD→HTML→XSS 清洗→高亮注入流水线。
    """
    html_body = _generate_html(text)
    # 将 re.findall 返回的 list 转换为 set，去除重复的语言标识
    langs_found = set(re.findall(r"language-([\w-]+)", html_body))
    scripts_html = _build_prism_scripts(langs_found)
    return HEAD + html_body + scripts_html + TAIL
