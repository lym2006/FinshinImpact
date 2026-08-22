# src/plugins/AI/services/render/css.py
"""
AI 回复渲染配置模块

提供：
- 用于生成 HTML 截图的 CSS 样式模板
- Prism 代码高亮组件映射
- HTML 标签与属性的安全白名单
"""

# ==================== 1. HTML 模板样式 ====================

HEAD = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-okaidia.min.css" rel="stylesheet" />
    <style>
        * {
            box-sizing: border-box; 
        }
        @font-face {
            font-family: 'SegUIEmoji';
            src: url('../../assets/seguiemj.ttf') format('truetype');
        }
        @font-face {
            font-family: 'MyMainFont';
            src: url('../../assets/font.ttf') format('truetype');
        }
        html {
            background: #FFA500;
            padding: 10px;
            margin: 0;
        }
        body {
            background-color: #ffffff; 
            width: fit-content;
            min-width: 580px;
            max-width: 960px;
            font-family: 'SegUIEmoji', 'MyMainFont', 'Segoe UI Emoji', sans-serif !important;
            font-size: 13px;
            line-height: 1.25;
            padding: 15px;
            margin: 0;
            color: #333;
            overflow-wrap: break-word;
            word-break: break-word;
        }
        p, ul, ol, blockquote, table, pre, figure, hr, div, h1, h2, h3, h4, h5, h6 {
            margin-top: 0.25em;
            margin-bottom: 0.25em;
        }
        li {
            margin-top: 0.05em;
            margin-bottom: 0.05em;
            line-height: 1.3;
        }
        table {
            table-layout: fixed;
            border-collapse: collapse;
            width: 100%;
        }
        th, td {
            min-width: 80px;
            padding: 8px;
            border: 1px solid #ddd;
            padding: 2px 4px;
            text-align: left;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        :not(pre) > code {
            background-color: #f0f0f0 !important;
            color: #e83e8c !important;
            padding: 1px 4px;
            border-radius: 2px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            font-size: 0.85em;
            white-space: pre-wrap;
            vertical-align: middle;
        }
        pre[class*="language-"] {
            margin: 0.25em 0 !important;
            padding: 6px !important;
            border-radius: 3px !important;
            border: 1px solid #444 !important;
            overflow: hidden !important;
            font-size: 11px !important;
            line-height: 1.3 !important;
            white-space: pre !important;
            word-wrap: normal !important;
        }
        pre code {
            margin: 0 !important;
            padding: 0;
            background: none;
            color: inherit;
            font-size: inherit;
            white-space: inherit;
        }
        blockquote {
            background-color: #f8f9fa;
            border-left: 3px solid #e338e6;
            margin: 0.5em 0 !important;
            padding: 5px 10px;
            color: #555;
            border-radius: 0 2px 2px 0;
            white-space: pre-wrap; 
        }
        body > :first-child { margin-top: 0; }
        body > :last-child { margin-bottom: 0; }
    </style>
</head>"""

TAIL = """
</body>
</html>"""

# ==================== 2. Prism 代码高亮组件映射 ====================

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

CDN_BASE = "https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/"

# ==================== 3. HTML 安全白名单配置 ====================

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
