import time
import asyncio
import logging
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramRetryAfter,TelegramBadRequest

from ..config import cupa
from ..core import rc,user_session,TaskItem,TaskStopped,make_data
from .client import ChatClient
from .render import screenshot,generate_html

logger=logging.getLogger("Bot.Plugins.AI.Worker")

trim=lambda text:text[-2000:] if len(text)>2000 else text

async def _send_long_message(task:TaskItem,text:str):
    total_len=len(text)
    for i in range(0,total_len,4000):
        chunk=text[i:i+4000]
        try:
            await task.safe_reply(chunk)
        except TelegramBadRequest as e:
            logger.error(f"❌ 分段消息 BadRequest: {e}")
        except:
            logger.error(f"❌ 分段消息未知错误: {Exception}")
        if total_len>4000*5:
            await asyncio.sleep(1)

async def _handle_ai_message(city:str,user:str):
    session=user_session[user]
    current_think=current_msg=""
    payload=make_data(session,city)
    try:
        async with ChatClient() as client:
            async for data in client.stream_chat(payload):
                logger.debug(f"🔍 流式返回的原始数据: {data}") 
                if "reasoning_content" in data and (content:=data["reasoning_content"]):
                    if content.endswith('\n'):
                        content=content[:-1]
                    current_think+=content
                    yield "think",current_think
                if "content" in data and (content:=data["content"]):
                    if content.startswith('\n\n'):
                        content=content[2:]
                    current_msg+=content
                    yield "chunk",content
            final_msg=current_msg
            final_think=current_think
            yield "final",(final_msg,final_think)
    except Exception as e:
        logger.error(f"❌ 流式请求异常: {e}")
        yield "error",str(e)

async def worker_loop(task:TaskItem,user:str):
    message=task.message
    city=message.text
    if not city:
        logger.warning("⚠️ 没有文本")
        return
    session=user_session[user]
    task.draft_id=int(time.time_ns()%2**63)
    task.last_draft_time=0
    error_msg=final_msg=final_think=""
    has_error=False
    try:
        async for event_type,data in _handle_ai_message(city,user):
            match event_type:
                case "think":
                    current_think=data
                    current_time=asyncio.get_event_loop().time()
                    if current_time-task.last_draft_time>1.2:
                        try:
                            preview_think=trim(current_think)
                            if await task.is_deleted():
                                raise TaskStopped()
                            if task.type==ChatType.PRIVATE:
                                success=await task.safe_draft(preview_think)
                                if success:
                                    task.last_draft_time=current_time
                        except TelegramRetryAfter as err:
                            if (t:=err.retry_after)>0:
                                logger.warning(f"⚠️ 触发频控，等待 {t} 秒...")
                                await asyncio.sleep(t)
                        except:
                            raise
                case "chunk": pass
                case "final":
                    final_msg,final_think=data
                case "error":
                    logger.error(f"❌ 流式处理错误: {data}")
                    has_error=True
                    error_msg=data
        try:
            if has_error:
                final_display_text=f"❌ 思考中断\n{error_msg}"
                logger.warning(f"⚠️ 思考中断")
            else:
                preview_think=trim(final_think)
                final_display_text=f"✅ 思考完成\n{preview_think}"
                logger.info(f"🚀 正在推送最终思考内容...")
            if await task.is_deleted():
                raise TaskStopped()
            if task.type==ChatType.PRIVATE:
                await task.safe_draft("\u061c")
            else:
                final_display_text="\u061c"
            await task.safe_edit(final_display_text)
        except TaskStopped:
            raise
        except:
            logger.warning(f"⚠️ UI 更新失败: {Exception}")
        if len(final_msg)>4000:
            await _send_long_message(task,final_msg)
        else:
            try:
                if task.type==ChatType.PRIVATE:
                    await task.safe_reply(final_msg)
                else:
                    await task.safe_edit(final_msg)
            except:
                raise
        session['message'].extend([rc("user",city),rc("assistant",final_msg)])
        session['md']=True
        print(final_msg)
        with open(cupa/f'{user}.html','w',encoding='utf-8') as a:
            a.write(generate_html(final_msg))
        wrt=f'{time.strftime("%Y-%m-%d %H:%M:%S",time.localtime())}\n\n用户：{city}\n\nAI思考：\n{final_think}\n\nAI回复：\n{final_msg}\n\n\n\n\n'
        open(cupa/f'{user}.txt','a',encoding='utf8').write(wrt)
        open(cupa/f'{user}.md','a',encoding='utf8').write(wrt)
        await screenshot(user,str(cupa/f'{user}.html'))
    except TaskStopped:
        raise
    except:
        logger.error(f"❌ Worker 运行时错误: {Exception}")
        await message.reply("❌ AI 对话服务暂不可用")