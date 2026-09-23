# src/plugins/AI/services/_render/_css.py
"""渲染样式（内部实现）

- 定义 CSS 模板与高亮组件映射
- 定义 HTML 安全白名单
"""

from ._theme import render_theme

# ==================== CDN 地址配置 ====================

# Prism CDN 根地址
_PRISM_CDN_ROOT = "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/"

# 子目录
_PRISM_COMPONENTS_DIR = "components/"
_PRISM_THEMES_DIR = "themes/"

# 派生 URL
_PRISM_THEME_URL = f"{_PRISM_CDN_ROOT}{_PRISM_THEMES_DIR}prism-okaidia.min.css"
CDN_BASE = f"{_PRISM_CDN_ROOT}{_PRISM_COMPONENTS_DIR}"

# ==================== HTML 模板样式 ====================

HEAD = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="{_PRISM_THEME_URL}" rel="stylesheet" />
    <style>
        * {{ box-sizing: {render_theme.box_sizing}; }}
        {render_theme.font_faces_css}
        html {{
            background: {render_theme.html_bg};
            padding: {render_theme.html_padding}px;
            margin: {render_theme.margin_reset};
        }}
        body {{
            background-color: {render_theme.body_bg}; 
            width: fit-content;
            min-width: {render_theme.body_min_width}px;
            max-width: {render_theme.body_max_width}px;
            font-family: {render_theme.font_css("body")} !important;
            font-size: {render_theme.body_font_size}px;
            line-height: {render_theme.body_line_height};
            padding: {render_theme.body_padding}px;
            margin: {render_theme.margin_reset};
            color: {render_theme.body_color};
            overflow-wrap: break-word;
            word-break: break-word;
        }}
        p, ul, ol, blockquote, table, pre, figure, hr, div, h1, h2, h3, h4, h5, h6 {{
            margin: {render_theme.margin_normal_css};
        }}
        li {{
            margin: {render_theme.margin_small_css};
            line-height: {render_theme.body_line_height};
        }}
        table {{
            table-layout: fixed;
            border-collapse: collapse;
            width: 100%;
        }}
        th, td {{
            min-width: {render_theme.cell_min_width}px;
            border: {render_theme.cell_border_width}px solid {render_theme.table_border_color};
            padding: {render_theme.cell_padding_css};
            text-align: left;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        th {{
            background-color: {render_theme.table_header_bg};
            font-weight: bold;
        }}
        :not(pre) > code {{
            background-color: {render_theme.code_bg} !important;
            color: {render_theme.code_color} !important;
            padding: {render_theme.code_padding_css};
            border-radius: {render_theme.code_radius}px;
            font-family: {render_theme.font_css("code")};
            font-size: {render_theme.code_font_size}em;
            white-space: pre-wrap;
            vertical-align: middle;
        }}
        pre[class*="language-"] {{
            margin: {render_theme.code_block_margin_css};
            padding: {render_theme.code_block_padding}px;
            border-radius: {render_theme.code_block_radius}px;
            border: {render_theme.code_block_border_width}px solid {render_theme.code_block_border_color};
            overflow: hidden;
            font-family: {render_theme.font_css("code")};
            font-size: {render_theme.code_block_font_size}px;
            line-height: {render_theme.code_block_line_height};
            white-space: pre;
            word-wrap: normal;
        }}
        pre code {{
            margin: {render_theme.margin_reset};
            padding: {render_theme.code_block_padding_reset};
            background: none;
            color: inherit;
            font-family: inherit;
            font-size: inherit;
            white-space: inherit;
        }}
        blockquote {{
            background-color: {render_theme.blockquote_bg};
            border-left: {render_theme.blockquote_border_width}px solid {render_theme.blockquote_border_color};
            margin: {render_theme.blockquote_margin_css};
            padding: {render_theme.blockquote_padding_css};
            color: {render_theme.blockquote_color};
            border-radius: {render_theme.blockquote_radius_css};
            white-space: pre-wrap;
        }}
        body > :first-child {{ margin-top: {render_theme.margin_reset}; }}
        body > :last-child {{ margin-bottom: {render_theme.margin_reset}; }}
    </style>
</head>"""

TAIL = """
</body>
</html>"""

# ==================== Prism 代码高亮组件映射 ====================

PRISM_COMPONENTS = {
    "python": "prism-python.min.js",
    "py": "prism-python.min.js",
    "bash": "prism-bash.min.js",
    "shell": "prism-bash.min.js",
    "sh": "prism-bash.min.js",
    "html": "prism-markup.min.js",
    "xml": "prism-markup.min.js",
    "json": "prism-json.min.js",
    "javascript": "prism-javascript.min.js",
    "js": "prism-javascript.min.js",
    "css": "prism-css.min.js",
    "sql": "prism-sql.min.js",
    "yaml": "prism-yaml.min.js",
    "yml": "prism-yaml.min.js",
    "markdown": "prism-markdown.min.js",
    "md": "prism-markdown.min.js",
    "diff": "prism-diff.min.js",
    "git": "prism-git.min.js",
}

# ==================== HTML 安全白名单配置 ====================

# 允许的 HTML 标签白名单（Markdown 渲染需要的标签 + 安全标签）
ALLOWED_TAGS = {
    # 基础文本
    "p",
    "br",
    "b",
    "strong",
    "i",
    "em",
    "u",
    "s",
    "strike",
    # 标题
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    # 列表
    "ul",
    "ol",
    "li",
    # 代码
    "pre",
    "code",
    "span",
    # 表格
    "table",
    "thead",
    "tbody",
    "tr",
    "th",
    "td",
    # 媒体和嵌入
    "figure",
    "img",
    # 链接
    "a",
    # 其他
    "blockquote",
    "div",
    "hr",
}

# 允许的标签属性（class 用于 Prism 高亮，href 用于链接）
ALLOWED_ATTRS = {
    "a": ["href", "title"],
    "code": ["class"],
    "pre": ["class"],
    "span": ["class"],
    "table": ["class"],
    "tr": ["class"],
    "th": ["class"],
    "td": ["class"],
    "blockquote": ["class"],
    "img": ["src", "alt", "title"],
}
