# src/finshin_sdk/_adapter.py
"""适配器契约

- 定义交互端口与适配器基类的抽象接口
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import Any

from .domain import MessageRoute, Platform, RouteSink
from .dto import MsgReferenceDTO, OutboundPayloadDTO, PrincipalDTO

# 清单编译器：把插件交出的路由清单编译成本平台的路由对象
RouterBuilder = Callable[[Sequence[MessageRoute]], Any]


class InteractionPort(ABC):
    """交互端口

    - 统一各平台的消息收发差异
    """

    @abstractmethod
    async def send_message(
        self,
        principal: PrincipalDTO,
        content: OutboundPayloadDTO,
        *,
        mention: bool = False,
        reply_ref: MsgReferenceDTO | None = None,
    ) -> MsgReferenceDTO | None:
        """发送消息

        - reply_ref 非空时引用该消息
        - mention 为真时提及目标主体
        """

    @abstractmethod
    async def probe_existence(self, target: MsgReferenceDTO) -> bool:
        """探测消息是否仍存在"""

    @abstractmethod
    def mention_fragment(self, principal: PrincipalDTO) -> str:
        """生成提及文本片段

        - 各平台返回格式不同，由子类实现
        """


class BaseAdapter(ABC):
    """平台适配器基类

    - 一个平台一个实例，生命周期归装载侧托管
    """

    @property
    @abstractmethod
    def platform(self) -> Platform:
        """平台标识"""

    @property
    @abstractmethod
    def interaction(self) -> InteractionPort:
        """交互端口"""

    @property
    @abstractmethod
    def route_sink(self) -> RouteSink:
        """插件路由的挂载口"""

    @property
    @abstractmethod
    def router_builder(self) -> RouterBuilder:
        """把路由清单编译成本平台路由的那只手"""

    @abstractmethod
    def attach_middleware(self, middleware: Any) -> None:
        """把日志中间件挂到本平台的更新链

        - 中间件实例由装载侧交来，挂载点各平台自己认
        """

    @abstractmethod
    async def start(self) -> None:
        """启动事件接收"""

    @abstractmethod
    async def stop(self) -> None:
        """停止事件接收"""

    @abstractmethod
    async def close(self) -> None:
        """释放连接资源

        - 轮询收尾必调，进程退出兜底再调一次
        """

    @abstractmethod
    def is_link_failure(self, exc: BaseException) -> bool:
        """判定异常属不属于链路故障

        - 链路故障按退避重试，其余异常直接上抛
        """
