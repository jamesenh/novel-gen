"""LangGraph SQLite Checkpointer（用于断点续跑）。

本项目不引入额外依赖（如 Postgres checkpointer 包），因此实现一个最小可用的
SQLite Checkpointer 来满足：
- 将 LangGraph 的 checkpoint 持久化到 `projects/<project>/workflow_checkpoints.db`
- 支持 `run` 过程中的自动 checkpoint
- 支持 `continue` 从最新 checkpoint 恢复并继续

实现参考 `langgraph.checkpoint.memory.InMemorySaver` 的行为与数据结构：
- checkpoint 本体（不含 channel_values）+ metadata
- channel_values 按 (channel, version) 分离存储为 blobs（节省重复存储）
- pending writes（用于 LangGraph 的内部一致性语义）
"""

from __future__ import annotations

import random
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any, Iterator, Sequence

from langgraph.checkpoint.base import (
    WRITES_IDX_MAP,
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
    RunnableConfig,
    get_checkpoint_id,
    get_checkpoint_metadata,
)


class SqliteCheckpointer(BaseCheckpointSaver[str]):
    """一个最小可用的 SQLite Checkpointer（单文件 DB）。"""

    def __init__(self, db_path: Path, *, serde=None) -> None:
        super().__init__(serde=serde)
        self._db_path = Path(db_path)

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        self._ensure_schema(conn)
        return conn

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS checkpoints (
              thread_id TEXT NOT NULL,
              checkpoint_ns TEXT NOT NULL,
              checkpoint_id TEXT NOT NULL,
              checkpoint_type TEXT NOT NULL,
              checkpoint_blob BLOB NOT NULL,
              metadata_type TEXT NOT NULL,
              metadata_blob BLOB NOT NULL,
              parent_checkpoint_id TEXT,
              created_at TEXT DEFAULT (datetime('now')),
              PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS blobs (
              thread_id TEXT NOT NULL,
              checkpoint_ns TEXT NOT NULL,
              channel TEXT NOT NULL,
              version TEXT NOT NULL,
              value_type TEXT NOT NULL,
              value_blob BLOB NOT NULL,
              PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS writes (
              thread_id TEXT NOT NULL,
              checkpoint_ns TEXT NOT NULL,
              checkpoint_id TEXT NOT NULL,
              task_id TEXT NOT NULL,
              write_idx INTEGER NOT NULL,
              channel TEXT NOT NULL,
              value_type TEXT NOT NULL,
              value_blob BLOB NOT NULL,
              task_path TEXT NOT NULL,
              PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, write_idx)
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_checkpoints_latest
            ON checkpoints(thread_id, checkpoint_ns, checkpoint_id)
            """
        )
        conn.commit()

    def _load_blobs(
        self,
        conn: sqlite3.Connection,
        thread_id: str,
        checkpoint_ns: str,
        versions: ChannelVersions,
    ) -> dict[str, Any]:
        channel_values: dict[str, Any] = {}
        cur = conn.cursor()
        for channel, version in versions.items():
            row = cur.execute(
                """
                SELECT value_type, value_blob
                FROM blobs
                WHERE thread_id=? AND checkpoint_ns=? AND channel=? AND version=?
                """,
                (thread_id, checkpoint_ns, channel, str(version)),
            ).fetchone()
            if not row:
                continue
            if row["value_type"] != "empty":
                channel_values[channel] = self.serde.loads_typed(
                    (row["value_type"], row["value_blob"])
                )
        return channel_values

    def _load_writes(
        self,
        conn: sqlite3.Connection,
        thread_id: str,
        checkpoint_ns: str,
        checkpoint_id: str,
    ) -> list[tuple[str, str, Any]]:
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT task_id, channel, value_type, value_blob
            FROM writes
            WHERE thread_id=? AND checkpoint_ns=? AND checkpoint_id=?
            ORDER BY task_id, write_idx
            """,
            (thread_id, checkpoint_ns, checkpoint_id),
        ).fetchall()
        pending: list[tuple[str, str, Any]] = []
        for r in rows:
            pending.append(
                (
                    r["task_id"],
                    r["channel"],
                    self.serde.loads_typed((r["value_type"], r["value_blob"])),
                )
            )
        return pending

    def _get_latest_checkpoint_id(
        self, conn: sqlite3.Connection, thread_id: str, checkpoint_ns: str
    ) -> str | None:
        row = conn.execute(
            """
            SELECT checkpoint_id
            FROM checkpoints
            WHERE thread_id=? AND checkpoint_ns=?
            ORDER BY checkpoint_id DESC
            LIMIT 1
            """,
            (thread_id, checkpoint_ns),
        ).fetchone()
        return row["checkpoint_id"] if row else None

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        thread_id: str = config["configurable"]["thread_id"]
        checkpoint_ns: str = config["configurable"].get("checkpoint_ns", "")
        parent_checkpoint_id = config["configurable"].get("checkpoint_id")

        c = checkpoint.copy()
        values: dict[str, Any] = c.pop("channel_values")  # type: ignore[misc]

        with closing(self._connect()) as conn:
            cur = conn.cursor()

            for channel, version in new_versions.items():
                value_type, value_blob = (
                    self.serde.dumps_typed(values[channel])
                    if channel in values
                    else ("empty", b"")
                )
                cur.execute(
                    """
                    INSERT OR REPLACE INTO blobs(
                      thread_id, checkpoint_ns, channel, version, value_type, value_blob
                    ) VALUES (?,?,?,?,?,?)
                    """,
                    (
                        thread_id,
                        checkpoint_ns,
                        channel,
                        str(version),
                        value_type,
                        value_blob,
                    ),
                )

            checkpoint_type, checkpoint_blob = self.serde.dumps_typed(c)
            meta_type, meta_blob = self.serde.dumps_typed(
                get_checkpoint_metadata(config, metadata)
            )
            cur.execute(
                """
                INSERT OR REPLACE INTO checkpoints(
                  thread_id, checkpoint_ns, checkpoint_id,
                  checkpoint_type, checkpoint_blob,
                  metadata_type, metadata_blob,
                  parent_checkpoint_id
                ) VALUES (?,?,?,?,?,?,?,?)
                """,
                (
                    thread_id,
                    checkpoint_ns,
                    checkpoint["id"],
                    checkpoint_type,
                    checkpoint_blob,
                    meta_type,
                    meta_blob,
                    parent_checkpoint_id,
                ),
            )
            conn.commit()

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint["id"],
            }
        }

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        thread_id: str = config["configurable"]["thread_id"]
        checkpoint_ns: str = config["configurable"].get("checkpoint_ns", "")

        with closing(self._connect()) as conn:
            checkpoint_id = get_checkpoint_id(config)
            if not checkpoint_id:
                checkpoint_id = self._get_latest_checkpoint_id(
                    conn, thread_id, checkpoint_ns
                )
                if not checkpoint_id:
                    return None

            row = conn.execute(
                """
                SELECT checkpoint_type, checkpoint_blob, metadata_type, metadata_blob, parent_checkpoint_id
                FROM checkpoints
                WHERE thread_id=? AND checkpoint_ns=? AND checkpoint_id=?
                """,
                (thread_id, checkpoint_ns, checkpoint_id),
            ).fetchone()
            if not row:
                return None

            checkpoint_: Checkpoint = self.serde.loads_typed(
                (row["checkpoint_type"], row["checkpoint_blob"])
            )
            checkpoint_full: Checkpoint = {
                **checkpoint_,
                "channel_values": self._load_blobs(
                    conn, thread_id, checkpoint_ns, checkpoint_["channel_versions"]
                ),
            }
            metadata_full = self.serde.loads_typed(
                (row["metadata_type"], row["metadata_blob"])
            )
            parent_checkpoint_id = row["parent_checkpoint_id"]
            pending_writes = self._load_writes(
                conn, thread_id, checkpoint_ns, checkpoint_id
            )

            return CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_ns": checkpoint_ns,
                        "checkpoint_id": checkpoint_id,
                    }
                },
                checkpoint=checkpoint_full,
                metadata=metadata_full,
                pending_writes=pending_writes,
                parent_config=(
                    {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": parent_checkpoint_id,
                        }
                    }
                    if parent_checkpoint_id
                    else None
                ),
            )

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        thread_id: str = config["configurable"]["thread_id"]
        checkpoint_ns: str = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id: str = config["configurable"]["checkpoint_id"]

        with closing(self._connect()) as conn:
            cur = conn.cursor()
            for idx, (channel, value) in enumerate(writes):
                write_idx = WRITES_IDX_MAP.get(channel, idx)
                if write_idx < 0:
                    continue
                value_type, value_blob = self.serde.dumps_typed(value)
                cur.execute(
                    """
                    INSERT OR IGNORE INTO writes(
                      thread_id, checkpoint_ns, checkpoint_id,
                      task_id, write_idx, channel,
                      value_type, value_blob, task_path
                    ) VALUES (?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        thread_id,
                        checkpoint_ns,
                        checkpoint_id,
                        task_id,
                        int(write_idx),
                        channel,
                        value_type,
                        value_blob,
                        task_path,
                    ),
                )
            conn.commit()

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        if not config:
            return iter(())

        thread_id: str = config["configurable"]["thread_id"]
        checkpoint_ns: str = config["configurable"].get("checkpoint_ns", "")
        before_id = get_checkpoint_id(before) if before else None

        params: list[Any] = [thread_id, checkpoint_ns]
        where = "WHERE thread_id=? AND checkpoint_ns=?"
        if before_id:
            where += " AND checkpoint_id < ?"
            params.append(before_id)

        sql = f"""
            SELECT checkpoint_id
            FROM checkpoints
            {where}
            ORDER BY checkpoint_id DESC
        """
        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))

        with closing(self._connect()) as conn:
            rows = conn.execute(sql, params).fetchall()
            for r in rows:
                cp_id = r["checkpoint_id"]
                tup = self.get_tuple(
                    {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_ns": checkpoint_ns,
                            "checkpoint_id": cp_id,
                        }
                    }
                )
                if not tup:
                    continue
                if filter:
                    # 最小实现：仅支持 metadata 的等值过滤（若字段不存在则不匹配）
                    ok = True
                    for k, v in filter.items():
                        if tup.metadata.get(k) != v:
                            ok = False
                            break
                    if not ok:
                        continue
                yield tup

    def get_next_version(self, current: str | None, channel: None) -> str:
        if current is None:
            current_v = 0
        elif isinstance(current, int):
            current_v = current
        else:
            current_v = int(str(current).split(".")[0])
        next_v = current_v + 1
        next_h = random.random()
        return f"{next_v:032}.{next_h:016}"
