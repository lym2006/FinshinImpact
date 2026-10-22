# src/data/_sqlite/_task.py
"""任务仓储实装

- 按任务 id 与主体键读写 task 表
- 状态推进按迁移表判定合法性
"""

import json
import time

import aiosqlite
from typing import cast

from core.contracts import TaskRepository
from core.domain import (
    ChatRole,
    Platform,
    TaskKind,
    TaskPayload,
    TaskPriority,
    TaskStatus,
)
from core.domain.ids import (
    KEY_SEP,
    ContainerKey,
    MessageId,
    PrincipalKey,
    TaskId,
    UserId,
)
from core.dto import (
    MsgReferenceDTO,
    PrincipalDTO,
    TaskDTO,
    TaskPatchDTO,
    TaskRequestDTO,
)

# 任务行的读取列，与仓储返回值一一对应
_TASK_COLUMNS = (
    "principal, kind, status, priority, source_ref, payload, "
    "created_at, started_at, finished_at, error"
)

# 状态迁移表，终态不出边
_ALLOWED_TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.PENDING: frozenset(
        {TaskStatus.RUNNING, TaskStatus.CANCELLED, TaskStatus.FAILED}
    ),
    TaskStatus.RUNNING: frozenset(
        {TaskStatus.SUCCEEDED, TaskStatus.CANCELLED, TaskStatus.FAILED}
    ),
    TaskStatus.SUCCEEDED: frozenset(),
    TaskStatus.CANCELLED: frozenset(),
    TaskStatus.FAILED: frozenset(),
}


class SqliteTaskRepository(TaskRepository):
    """任务仓储的 SQLite 实装"""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        self._conn = conn

    async def insert(self, request: TaskRequestDTO) -> TaskDTO:
        """落库新任务

        - 去重键命中未完成任务时返回既有任务
        - 同 id 重写即覆盖，起终时间与错误清空
        """
        if request.dedupe_key:
            existing = await self._find_active_by_dedupe(request.dedupe_key)
            if existing is not None:
                return existing

        now = time.time()
        await self._conn.execute(
            "INSERT INTO task(id, principal, kind, priority, sequence, status,"
            " payload, source_ref, dedupe_key, created_at)"
            " VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET"
            " priority = excluded.priority, sequence = excluded.sequence,"
            " status = excluded.status, payload = excluded.payload,"
            " source_ref = excluded.source_ref, dedupe_key = excluded.dedupe_key,"
            " error = '', started_at = NULL, finished_at = NULL",
            (
                TaskId(f"{request.principal.key}{KEY_SEP}{request.kind}"),
                request.principal.key,
                request.kind,
                request.priority,
                await self._next_sequence(request.principal.key),
                TaskStatus.PENDING,
                _encode_payload(request.payload),
                _encode_ref(request.source_ref),
                request.dedupe_key,
                now,
            ),
        )
        await self._conn.commit()

        return TaskDTO(
            principal=request.principal,
            kind=request.kind,
            status=TaskStatus.PENDING,
            priority=request.priority,
            source_ref=request.source_ref,
            payload=request.payload,
            created_at=now,
        )

    async def patch(self, task_id: TaskId, patch: TaskPatchDTO) -> TaskDTO | None:
        """更新任务

        - 任务不存在或状态迁移非法返回 None
        """
        current = await self.find(task_id)
        if current is None:
            return None

        assignments: list[str] = []
        params: list[object] = []
        if patch.status is not None:
            if patch.status not in _ALLOWED_TRANSITIONS[current.status]:
                return None
            assignments.append("status = ?")
            params.append(patch.status)
            now = time.time()
            if patch.status is TaskStatus.RUNNING:
                assignments.append("started_at = ?")
                params.append(now)
            elif not _ALLOWED_TRANSITIONS[patch.status]:
                assignments.append("finished_at = ?")
                params.append(now)
        if patch.error_text is not None:
            assignments.append("error = ?")
            params.append(patch.error_text)

        if not assignments:
            return current

        params.append(task_id)
        await self._conn.execute(
            f"UPDATE task SET {', '.join(assignments)} WHERE id = ?", params
        )
        await self._conn.commit()
        return await self.find(task_id)

    async def find(self, task_id: TaskId) -> TaskDTO | None:
        """按 ID 查询"""
        async with self._conn.execute(
            f"SELECT {_TASK_COLUMNS} FROM task WHERE id = ?", (task_id,)
        ) as cursor:
            row = await cursor.fetchone()
        return self._to_dto(row) if row is not None else None

    async def list_unfinished(self, key: PrincipalKey) -> tuple[TaskDTO, ...]:
        """列出主体未完成任务

        - 优先级升序、同优先级按入队序
        """
        async with self._conn.execute(
            f"SELECT {_TASK_COLUMNS} FROM task "
            "WHERE principal = ? AND status IN (?, ?)"
            " ORDER BY priority, sequence",
            (key, TaskStatus.PENDING, TaskStatus.RUNNING),
        ) as cursor:
            rows = await cursor.fetchall()
        return tuple(self._to_dto(row) for row in rows)

    async def delete_by_principal(self, key: PrincipalKey) -> int:
        """清除主体全部任务"""
        async with self._conn.execute(
            "DELETE FROM task WHERE principal = ?", (key,)
        ) as cursor:
            removed = cursor.rowcount
        await self._conn.commit()
        return removed

    async def _next_sequence(self, key: PrincipalKey) -> int:
        """取主体内下一个入队序号"""
        async with self._conn.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 FROM task WHERE principal = ?",
            (key,),
        ) as cursor:
            # 聚合查询恒有一行
            row = cast("aiosqlite.Row", await cursor.fetchone())
        return int(row[0])

    async def _find_active_by_dedupe(self, dedupe_key: str) -> TaskDTO | None:
        """按去重键取未完成的同内容任务"""
        async with self._conn.execute(
            "SELECT "
            f"{_TASK_COLUMNS} FROM task "
            "WHERE dedupe_key = ? AND status IN (?, ?)",
            (dedupe_key, TaskStatus.PENDING, TaskStatus.RUNNING),
        ) as cursor:
            row = await cursor.fetchone()
        return self._to_dto(row) if row is not None else None

    def _to_dto(self, row: aiosqlite.Row) -> TaskDTO:
        """行转任务快照"""
        platform, container, user = row["principal"].split(KEY_SEP, 2)
        source = json.loads(row["source_ref"])
        return TaskDTO(
            principal=PrincipalDTO(
                platform=Platform(platform),
                container=ContainerKey(container),
                user=UserId(user),
            ),
            kind=TaskKind(row["kind"]),
            status=TaskStatus(row["status"]),
            priority=TaskPriority(row["priority"]),
            source_ref=MsgReferenceDTO(
                platform=Platform(source["platform"]),
                container=ContainerKey(source["container"]),
                message_id=MessageId(source["message_id"]),
            ),
            payload=_decode_payload(row["payload"]),
            created_at=row["created_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            error_text=row["error"],
        )


def _encode_payload(payload: TaskPayload) -> str:
    """对话轮次编码为 JSON"""
    return json.dumps([[str(role), text] for role, text in payload], ensure_ascii=False)


def _decode_payload(raw: str) -> TaskPayload:
    """JSON 解码为对话轮次"""
    return tuple((ChatRole(role), text) for role, text in json.loads(raw))


def _encode_ref(ref: MsgReferenceDTO) -> str:
    """消息定位三元组编码为 JSON"""
    return json.dumps(
        {
            "platform": str(ref.platform),
            "container": ref.container,
            "message_id": ref.message_id,
        },
        ensure_ascii=False,
    )
