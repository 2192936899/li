from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sqlite3
from typing import Any


class MeetingStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS meetings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    transcript TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    tasks_json TEXT NOT NULL,
                    risks_json TEXT NOT NULL
                )
                """
            )

    def save(
        self,
        title: str,
        transcript: str,
        summary: str,
        tasks: list[dict[str, Any]],
        risks: list[dict[str, Any]],
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO meetings (title, created_at, transcript, summary, tasks_json, risks_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    datetime.now().isoformat(timespec="seconds"),
                    transcript,
                    summary,
                    json.dumps(tasks, ensure_ascii=False),
                    json.dumps(risks, ensure_ascii=False),
                ),
            )
            return int(cursor.lastrowid)

    def list_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, title, created_at, summary, tasks_json, risks_json
                FROM meetings
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]


class MeetingMemory:
    def __init__(self, persist_dir: Path) -> None:
        self.enabled = False
        self.collection = None
        try:
            import chromadb

            client = chromadb.PersistentClient(path=str(persist_dir))
            self.collection = client.get_or_create_collection("meetings")
            self.enabled = True
        except Exception:
            self.enabled = False

    def add(self, meeting_id: int, title: str, transcript: str, summary: str) -> None:
        if not self.enabled or self.collection is None:
            return
        document = f"# {title}\n\n## Summary\n{summary}\n\n## Transcript\n{transcript}"
        self.collection.add(
            ids=[str(meeting_id)],
            documents=[document],
            metadatas=[{"title": title}],
        )
