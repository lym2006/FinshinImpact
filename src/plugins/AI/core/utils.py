import logging
from typing import Any
from tenacity import retry,stop_after_attempt,wait_exponential,retry_if_exception_type
from aiogram.types import Message
from aiogram.exceptions import TelegramNetworkError

rc=lambda role,content:{"role":role,"content":content}
logger=logging.getLogger("Bot.Plugins.AI.Retry")

def make_data(session:dict[str,Any],thisinput:str) -> list:
    return session['message']+[rc('user',thisinput)]

def get_name(msg:Message) -> str:
    id=msg.chat.id
    return f"g_{abs(id)}_{getattr(getattr(msg,'from_user',None),'id','unknown')}" if id<0 else f"u_{id}"

def retry_sending(max_retries=3):
    return retry(
        retry=retry_if_exception_type(TelegramNetworkError),
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=1,max=10,min=1),
        before= lambda retry_state: logger.warning(
            f"⚠️ 消息发送失败，正在第 {retry_state.attempt_number-1} 次重试..."
        ) if retry_state.attempt_number>1 else None,
        reraise=True
    )