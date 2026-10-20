# src/core/domain/ids.py
"""标识值类型

- 为跨 DTO 共用的字符串段定义语义类型
- NewType 运行时即原 str，仅静态检查区分段义
"""

from typing import NewType

# 联合键分段符，键串即文件名安全串
KEY_SEP = "."

# 容器与键段
ContainerKey = NewType("ContainerKey", str)  # g/u 前缀
UserKey = NewType("UserKey", str)  # platform.user
SessionKey = NewType("SessionKey", str)  # SessionDTO.key
MessageKey = NewType("MessageKey", str)  # MsgReferenceDTO.key
PrincipalKey = NewType("PrincipalKey", str)  # PrincipalDTO.key
ConfigPath = NewType("ConfigPath", str)  # 配置段.键

# 平台原始标识
UserId = NewType("UserId", str)
MessageId = NewType("MessageId", str)
TaskId = NewType("TaskId", str)  # f"{PrincipalDTO.key}.{TaskKind}"
