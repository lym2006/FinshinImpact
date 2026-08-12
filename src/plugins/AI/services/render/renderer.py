import re
from markdown import markdown as md

from .css import head,tail,CDN_BASE,PRISM_COMPONENTS

def generate_html(msg:str) -> str:
    html_body=md(
            msg,
            extensions=['fenced_code','tables','nl2br','codehilite'],
            extension_configs={
                'codehilite':{
                    'linenums':False,
                    'use_pygments':False,
                    'lang_prefix':'language-'
                }
            }
        )
    langs_found=set(re.findall(r'language-([\w-]+)',html_body))
    scripts=['\n<script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>']
    for lang in langs_found:
        lang_key=lang.lower()
        if lang_key in PRISM_COMPONENTS:
            js_file=PRISM_COMPONENTS[lang_key]
            scripts.append(f'<script src="{CDN_BASE}{js_file}"></script>')
    scripts_html="\n".join(scripts)
    final_html=head+html_body+scripts_html+tail
    return final_html