from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum


class AlertLevel(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    DROWSY = "DROWSY"


@dataclass(frozen=True)
class DrowsinessConfig:
    eye_closed_seconds: float = 1.5
    warning_closed_seconds: float = 0.7
    yawn_seconds: float = 2.0
    perclos_window_seconds: float = 30.0
    perclos_warning: float = 0.20
    perclos_alarm: float = 0.35
    missing_face_seconds: float = 2.0


@dataclass(frozen=True)
class DrowsinessState:
    level: AlertLevel
    ear: float | None
    mar: float | None
    perclos: float
    eye_closed_for: float
    face_missing_for: float
    yawns: int
    reasons: tuple[str, ...]


class DrowsinessEngine:
    """Time-based decision engine independent of camera frame rate."""

    def __init__(self, config: DrowsinessConfig | None = None) -> None:
        self.config = config or DrowsinessConfig()
        self._eye_closed_since: float | None = None
        self._mouth_open_since: float | None = None
        self._face_missing_since: float | None = None
        self._last_yawn_at: float | None = None
        self._yawns = 0
        self._samples: deque[tuple[float, bool]] = deque()

    def update(
        self,
        timestamp: float,
        *,
        face_detected: bool,
        ear: float | None,
        mar: float | None,
        ear_threshold: float,
        mar_threshold: float = 0.60,
    ) -> DrowsinessState:
        cfg = self.config
        eye_closed = face_detected and ear is not None and ear < ear_threshold
        mouth_open = face_detected and mar is not None and mar > mar_threshold

        if face_detected:
            self._face_missing_since = None
        elif self._face_missing_since is None:
            self._face_missing_since = timestamp

        if eye_closed:
            if self._eye_closed_since is None:
                self._eye_closed_since = timestamp
        else:
            self._eye_closed_since = None

        if mouth_open:
            if self._mouth_open_since is None:
                self._mouth_open_since = timestamp
        elif self._mouth_open_since is not None:
            if timestamp - self._mouth_open_since >= cfg.yawn_seconds:
                if self._last_yawn_at is None or timestamp - self._last_yawn_at > 1.0:
                    self._yawns += 1
                    self._last_yawn_at = timestamp
            self._mouth_open_since = None

        self._samples.append((timestamp, eye_closed))
        cutoff = timestamp - cfg.perclos_window_seconds
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()

        perclos = self._calculate_perclos()
        closed_for = 0.0 if self._eye_closed_since is None else timestamp - self._eye_closed_since
        missing_for = 0.0 if self._face_missing_since is None else timestamp - self._face_missing_since

        reasons: list[str] = []
        level = AlertLevel.NORMAL
        if closed_for >= cfg.eye_closed_seconds:
            level = AlertLevel.DROWSY
            reasons.append(f"eyes closed {closed_for:.1f}s")
        elif missing_for >= cfg.missing_face_seconds:
            level = AlertLevel.DROWSY
            reasons.append(f"face missing {missing_for:.1f}s")
        elif perclos >= cfg.perclos_alarm and self._window_ready():
            level = AlertLevel.DROWSY
            reasons.append(f"PERCLOS {perclos:.0%}")
        elif closed_for >= cfg.warning_closed_seconds:
            level = AlertLevel.WARNING
            reasons.append(f"eyes closing {closed_for:.1f}s")
        elif perclos >= cfg.perclos_warning and self._window_ready():
            level = AlertLevel.WARNING
            reasons.append(f"PERCLOS {perclos:.0%}")

        return DrowsinessState(
            level=level,
            ear=ear,
            mar=mar,
            perclos=perclos,
            eye_closed_for=closed_for,
            face_missing_for=missing_for,
            yawns=self._yawns,
            reasons=tuple(reasons),
        )

    def _window_ready(self) -> bool:
        if len(self._samples) < 2:
            return False
        return self._samples[-1][0] - self._samples[0][0] >= min(
            10.0, self.config.perclos_window_seconds
        )

    def _calculate_perclos(self) -> float:
        if len(self._samples) < 2:
            return 0.0
        closed_time = 0.0
        total_time = 0.0
        previous_time, previous_closed = self._samples[0]
        for current_time, current_closed in list(self._samples)[1:]:
            delta = max(0.0, current_time - previous_time)
            total_time += delta
            if previous_closed:
                closed_time += delta
            previous_time, previous_closed = current_time, current_closed
        return closed_time / total_time if total_time else 0.0

