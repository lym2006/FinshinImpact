# src/core/contracts/_adapter.py
"""适配器契约

- 定义交互端口与适配器基类的抽象接口
"""

from abc import ABC, abstractmethod

from ..domain import Platform
from ..dto import MsgReferenceDTO, OutboundPayloadDTO, PrincipalDTO


class InteractionPort(ABC):
    """交互端口

    - 屏蔽平台底层差异
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
        - 具体引用和提及实现由 Adapter 内部处理
        """

    @abstractmethod
    async def probe_existence(self, target: MsgReferenceDTO) -> bool:
        """探测消息是否仍存在"""

    @abstractmethod
    def mention_fragment(self, principal: PrincipalDTO) -> str:
        """生成提及文本片段

        - 纯字符串拼装，不发请求
        - 不同平台返回格式不同，由 Adapter 决定
        """


class BaseAdapter(ABC):
    """平台适配器基类

    - 一个平台一个实例，生命周期由 AdapterRuntime 托管
    """

    @property
    @abstractmethod
    def platform(self) -> Platform:
        """平台标识"""

    @property
    @abstractmethod
    def interaction(self) -> InteractionPort:
        """交互端口"""

    @abstractmethod
    async def start(self) -> None:
        """启动事件接收"""

    @abstractmethod
    async def stop(self) -> None:
        """停止并释放连接"""
