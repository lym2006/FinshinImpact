# src/plugins/AI/services/render/renderer.py
"""
Markdown 渲染服务

负责：
- Markdown 转 HTML 渲染（含 XSS 清洗）
- Prism.js 语法高亮脚本动态注入
"""

import re

import bleach
from markdown import markdown as md

from .css import ALLOWED_ATTRS, ALLOWED_TAGS, CDN_BASE, HEAD, PRISM_COMPONENTS, TAIL


# ==================== 1. Markdown 转 HTML ====================
def _generate_html(text: str) -> str:
    """将 Markdown 文本转换为包含完整 HTML 结构的字符串"""
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


# ==================== 2. Prism 脚本注入 ====================
def _build_prism_scripts(langs_found: set[str]) -> str:
    """根据检测到的代码语言构建 Prism.js 的 <script> 标签，未检测到代码时返回空字符串"""
    # 提取所有代码块的语言标识
    # langs_found = set(re.findall(r"language-([\w-]+)", html_body))
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


# ==================== 3. 渲染主入口 ====================
def render_html(text: str) -> str:
    """将 Markdown 文本渲染为完整的 HTML 页面（含样式 + 语法高亮）

    对外暴露的统一入口，内部自动完成：Markdown 转 HTML → XSS 清洗 →
    检测代码语言 → 注入 Prism 脚本 → 拼装完整页面。
    """
    html_body = _generate_html(text)
    # 将 re.findall 返回的 list 转换为 set，去除重复的语言标识
    langs_found = set(re.findall(r"language-([\w-]+)", html_body))
    scripts_html = _build_prism_scripts(langs_found)
    return HEAD + html_body + scripts_html + TAIL
