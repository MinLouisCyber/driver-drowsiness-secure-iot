from __future__ import annotations

import threading
import time
from typing import Any


class MonitorRuntime:
    """Thread-safe bridge between the camera worker and Flask dashboard."""

    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._frame: bytes | None = None
        self._frame_version = 0
        self._status: dict[str, Any] = {
            "camera": "STARTING",
            "mqtt": "DISCONNECTED",
            "esp32": "WAITING",
            "level": "CALIBRATING",
            "message": "Đang khởi động camera",
            "face_detected": False,
            "ear": None,
            "left_ear": None,
            "right_ear": None,
            "mar": None,
            "mouth_open": False,
            "perclos": 0.0,
            "eye_closed_for": 0.0,
            "yawns": 0,
            "reasons": [],
            "updated_at": int(time.time()),
        }

    def publish_frame(self, jpeg: bytes) -> None:
        with self._condition:
            self._frame = jpeg
            self._frame_version += 1
            self._condition.notify_all()

    def update_status(self, **values: Any) -> None:
        with self._condition:
            self._status.update(values)
            self._status["updated_at"] = int(time.time())

    def status(self) -> dict[str, Any]:
        with self._condition:
            return dict(self._status)

    def wait_for_frame(
        self, previous_version: int, timeout: float = 2.0
    ) -> tuple[int, bytes | None]:
        with self._condition:
            self._condition.wait_for(
                lambda: self._frame_version != previous_version,
                timeout=timeout,
            )
            return self._frame_version, self._frame

