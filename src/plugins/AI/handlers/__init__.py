# src/plugins/AI/handlers/__init__.py
"""
AI 路由注册中心

导出：
- 统一的路由工厂函数：用于生成聚合所有子模块的路由
"""

from aiogram import Router

from . import ai_chat, auth, history

# , identity


# ==================== 1. 路由组装工厂 ====================
def get_router() -> Router:
    """组装并返回包含所有 AI 业务路由的总路由器"""
    router = Router()

    # 注册所有子路由（顺序即优先级）
    # 确保 ai_chat 是最后一个注册
    routers = [
        auth.auth,
        history.history,
        # identity.identity,
        ai_chat.ai_chat,
    ]
    for r in routers:
        router.include_router(r)

    return router


# ==================== 2. 模块公开接口声明 ====================

__all__ = ["get_router"]
