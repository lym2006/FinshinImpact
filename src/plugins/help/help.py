import re
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

from aiogram import Router
from aiogram.types import Message,FSInputFile
from aiogram.filters import Command,Filter

router=Router()

cupa=Path.cwd()/'src/plugins/help'
fontp=Path.cwd()/'assets/font.ttf'
notice={#命令和空格共占10位，其中中文占2位
    0:"Fool的功能列表\n注：只有少量命令后可带参数\n请不要删除机器人发出的提示消息",
    "help":"查看帮助文档，命令后接-h可以单独查看该命令帮助",
    1:"\nAI部分\n独立会话和思考过程",
    "on":"开启AI对话",
    "off":"关闭AI对话",
    "md":"以markdown格式输出上一次回复内容（图片）",
    "history":"显示历史记录（包括思考过程）",
    "clear":"清空记忆",
    "balance":"查看账户余额",
    #"change":"更改AI人设",
    #"system":"以system身份输入数据，用于添加人设、背景等",
    2:"\n未完待续"
}

#############################################################################################################################################################

class startwithslash(Filter):
    async def __call__(self,message:Message)->bool:
        if not message.text:
            return False
        if not message.text.startswith('/'):
            return False
        mes=message.text[1:].split()
        return not any(c in notice for c in mes)
@router.message(startwithslash())
async def command_check(message:Message):
    st=message.text
    if not st:
        return
    st=re.sub(' ','',st)
    st=re.sub('/','',st)
    if st not in notice:
        await message.answer("命令不存在，请使用 /help ")

#############################################################################################################################################################

class keywordfilter(Filter):
    async def __call__(self,message:Message)->bool:
        if not message.text:
            return False
        if not message.text.startswith('/'):
            return False
        mes=message.text[1:].split()
        return ('-h' in mes) and any(c in notice for c in mes)
@router.message(keywordfilter())
async def command_help(message:Message):
    st=message.text
    if not st:
        await message.answer("格式错误")
        return
    t=st.index('-')
    st=st[:t]
    st=re.sub(' ','',st)
    st=re.sub('/','',st)
    if st in notice:
        await message.answer(notice[st])
    else:
        await message.answer("格式错误")

#############################################################################################################################################################

def count(text):
    pattern=re.compile(r'[\u4e00-\u9fa5]')
    Chinese=re.findall(pattern, text)
    return len(Chinese)*2+(len(text)-len(Chinese))

@router.message(Command('help'))
async def show_help_list(message:Message):
    msg=''
    m=0
    for k,v in notice.items():
        if(type(k)==str):
            p=f'/{k}'
            t=count(k)+1
            msg+=p
            m=max(m,len(p+v))
            v=' '*(10-t)+v
        msg+=f'{v}\n'
    fonts=30
    line=msg.split('\n')
    img=Image.new('RGB',((fonts+5)*m,len(line)*(fonts+5)),(255,255,255))
    dr=ImageDraw.Draw(img)
    font=ImageFont.truetype(fontp,fonts)
    dr.text((20,20),msg,font=font,fill="#000000")
    pa=cupa/'out.jpg'
    Path(pa).unlink(missing_ok=True)
    img.save(pa)
    await message.answer_photo(FSInputFile(str(pa)))
    Path(pa).unlink