import logging
from datetime import datetime
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..services.client import ChatClient

balance=Router()
logger=logging.getLogger("Bot.Plugins.AI.Balance")

@balance.message(Command('balance'))#查询余额
async def check_balance(message:Message):
    try:
        async with ChatClient() as client:
            resp=await client.get("/user/info")
        balance=resp.json()['data']['balance']
        charge=resp.json()['data']['chargeBalance']
        total=resp.json()['data']['totalBalance']
        report_lines=[
            "💰账户余额",
            f"余额：{balance}",
            f"氪金：{charge}",
            f"总计：{total}",
            f"更新时间：{datetime.now().strftime('%m-%d %H:%M')}"
        ]
        await message.answer("\n".join(report_lines))
    except:
        logger.error(f"查询失败\n{str(Exception)}")
        await message.answer(f"查询失败")