from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any


class EventStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp INTEGER NOT NULL,
                        sequence INTEGER NOT NULL,
                        device_id TEXT NOT NULL,
                        status TEXT NOT NULL,
                        accepted INTEGER NOT NULL,
                        verification_reason TEXT NOT NULL,
                        payload TEXT NOT NULL
                    )
                    """
                )

    def add(self, event: dict[str, Any], accepted: bool, reason: str) -> None:
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO events
                        (timestamp, sequence, device_id, status, accepted,
                         verification_reason, payload)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        int(event.get("timestamp", 0)),
                        int(event.get("sequence", -1)),
                        str(event.get("device_id", "unknown")),
                        str(event.get("status", "UNKNOWN")),
                        int(accepted),
                        reason,
                        json.dumps(event, ensure_ascii=False, sort_keys=True),
                    ),
                )

    def latest(self, limit: int = 100) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

