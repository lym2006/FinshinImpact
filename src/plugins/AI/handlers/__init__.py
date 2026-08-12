from aiogram import Router

from . import auth,balance,history,identity,AIchat

def get_router():
    router=Router()
    routers=[
        auth.auth,
        balance.balance,
        history.history,
        identity.identity,
        AIchat.chat
    ]
    for r in routers:
        router.include_router(r)
    return router

__all__=["get_router"]