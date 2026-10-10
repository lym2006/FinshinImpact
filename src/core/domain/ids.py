# src/core/domain/ids.py
"""标识值类型

- 为跨 DTO 复用的字符串段定义语义类型
- NewType 运行时即原 str，仅静态检查区分段义
"""

from typing import NewType

# 容器与键段
Container = NewType("Container", str)  # g/u 前缀
UserKey = NewType("UserKey", str)  # platform:user
SessionKey = NewType("SessionKey", str)  # SessionDTO.key
MessageKey = NewType("MessageKey", str)  # MsgReferenceDTO.key
PrincipalKey = NewType("PrincipalKey", str)  # PrincipalDTO.key

# 平台原始标识
UserId = NewType("UserId", str)
MessageId = NewType("MessageId", str)
TaskId = NewType("TaskId", str)  # MessageKey:TaskKind
