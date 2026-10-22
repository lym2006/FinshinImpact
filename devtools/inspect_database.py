# devtools/inspect_database.py
"""实例库只读查看

- 打印 schema 版本、各表行数、会话概览与指定会话的消息明细
- 只以只读模式打开库文件，不建库、不迁移、不写行
- 会话键与消息时间戳按库内原样列出，便于对着代码核接线
"""

import argparse
import sqlite3
import sys
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_DB_GLOB = "instances/*/db/bot.db"
_BODY_WIDTH = 80  # 明细正文截断宽度，约合四十个中文
_DEFAULT_LIMIT = 20


def _find_dbs(db: str) -> list[Path]:
    """定位待查看的库文件

    - 给了路径只看那一份，否则扫全部实例
    """
    if db:
        path = Path(db)
        return [] if not path.is_file() else [path]
    return sorted(_ROOT.glob(_DB_GLOB))


def _format_at(epoch: float | None) -> str:
    """把秒级时间戳换成本地时间串

    - 空值显示短横，免得读成 1970
    """
    if epoch is None:
        return "-"
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M:%S")


def _tables(conn: sqlite3.Connection) -> list[str]:
    """取库内全部表名

    - 视图与索引不计，空库即零张
    """
    return [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    ]


def _sessions(conn: sqlite3.Connection) -> Iterator[tuple[str, str, int, float, str]]:
    """逐条产出会话概览

    - 消息数按会话键现算，不依赖计数列
    """
    return conn.execute(
        """SELECT s.key, s.container_name,
                  (SELECT COUNT(*) FROM session_message m
                    WHERE m.session_key = s.key) AS msgs,
                  s.last_active_at, s.summary
           FROM session s
          ORDER BY s.last_active_at DESC"""
    )


def _print_overview(conn: sqlite3.Connection, path: Path) -> None:
    """打印库概览

    - 没有表即判未迁移，只报这一条不追行数
    """
    print(f"库：{path}")
    print(f"大小：{path.stat().st_size} 字节")
    tables = _tables(conn)
    if not tables:
        print("空库：一张表都没有，程序启动跑一次迁移后即有结构")
        return

    print(f"schema 版本：{_schema_version(conn)}")
    for table in tables:
        count = conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        print(f"  {table}：{count} 行")

    print("会话概览：")
    rows = list(_sessions(conn))
    if not rows:
        print("  （无会话行）")
    for key, name, msgs, last, summary in rows:
        print(f"  {key} 容器名={name or '-'} 消息={msgs} 活跃={_format_at(last)}")
        print(f"    摘要：{summary or '（空）'}")


def _schema_version(conn: sqlite3.Connection) -> str:
    """取版本行的最大版本号

    - 版本表缺失或无行时如实报出，不兜成 0
    """
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return "-" if row[0] is None else str(row[0])


def _print_session(conn: sqlite3.Connection, key: str, limit: int) -> None:
    """打印指定会话最近的若干轮

    - 按 seq 升序输出，正文超宽截断加省略号
    """
    rows = conn.execute(
        """SELECT seq, role, sender_id, sender_name, content, created_at
           FROM session_message WHERE session_key = ?
          ORDER BY seq DESC LIMIT ?""",
        (key, limit),
    ).fetchall()
    if not rows:
        print(f"会话 {key} 没有消息行")
        return

    print(f"会话 {key} 最近 {len(rows)} 条：")
    for seq, role, sender_id, sender_name, content, created_at in reversed(rows):
        who = f"{sender_name}({sender_id})" if sender_name or sender_id else "-"
        cut = content[:_BODY_WIDTH] + ("…" if len(content) > _BODY_WIDTH else "")
        print(f"  #{seq} {role} {_format_at(created_at)} {who}")
        print(f"      {cut}")


def main() -> int:
    """解析参数并输出概览与可选明细"""
    parser = argparse.ArgumentParser(description="只读查看实例库")
    parser.add_argument("--db", default="", help="库文件路径，缺省扫全部实例")
    parser.add_argument("--session", default="", help="会话键，给出即列该会话消息")
    parser.add_argument(
        "-n", "--limit", type=int, default=_DEFAULT_LIMIT, help="明细条数上限"
    )
    args = parser.parse_args()

    dbs = _find_dbs(args.db)
    if not dbs:
        print("没找到库文件，先启动一次程序建库，或用 --db 指定路径")
        return 1

    for path in dbs:
        conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
        try:
            _print_overview(conn, path)
            if args.session:
                _print_session(conn, args.session, args.limit)
        finally:
            conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
