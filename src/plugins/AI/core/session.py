import copy
import time
import asyncio
import functools
from typing import Any
from aiogram.types import Message

from ..config import ini,cupa
from .utils import get_name
from .task import TaskQueue

user_session:dict[str,dict[str,Any]]={}
active_tasks:set[asyncio.Task]=set()

DEFAULT_SESSION={
    'message':ini,
    'md':False,
    'is_active':False,
    'last_active':time.time()
}

def create_new_session() -> dict[str,Any]:
    new_session=copy.deepcopy(DEFAULT_SESSION)
    return new_session

def session_guard(func):
    @functools.wraps(func)
    async def wrapper(message:Message,*args,**kwargs):
        user=get_name(message)
        if user not in user_session:
            user_session[user]=create_new_session()
            print(f"🆕 [Decorator] 已为 {user} 初始化会话")
            file_path=cupa/f"{user}.md"
            file_path.unlink(missing_ok=True)
            con=ini[0]['content']
            wrt=f'{time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())}\n\n系统：\n{con}\n\n\n\n\n'
            open(file_path,'a',encoding='utf-8').write(wrt)
        if 'queue' not in user_session[user]:
            user_session[user]['queue']=TaskQueue()
        return await func(message,*args,**kwargs)
    return wrapper