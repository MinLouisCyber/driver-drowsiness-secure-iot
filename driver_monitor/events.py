from __future__ import annotations

import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .security import EventSigner, EventVerifier, VerificationResult
from .state import DrowsinessState
from .storage import EventStore


class EventPipeline:
    def __init__(
        self,
        database: str | Path,
        *,
        device_id: str | None = None,
        secret: str | None = None,
    ) -> None:
        device_id = device_id or os.getenv("DRIVER_DEVICE_ID", "LAPTOP-CAM-01")
        secret = secret or os.getenv("DRIVER_DEVICE_SECRET", "change-this-demo-secret")
        self.signer = EventSigner(device_id, secret)
        self.verifier = EventVerifier({device_id: secret})
        self.store = EventStore(database)
        self.sequence = 0

    def publish_state(self, state: DrowsinessState) -> tuple[dict[str, Any], VerificationResult]:
        self.sequence += 1
        event = {
            "timestamp": int(time.time()),
            "sequence": self.sequence,
            "status": state.level.value,
            "ear": None if state.ear is None else round(state.ear, 4),
            "mar": None if state.mar is None else round(state.mar, 4),
            "perclos": round(state.perclos, 4),
            "yawns": state.yawns,
            "reasons": list(state.reasons),
        }
        signed = self.signer.sign(event)
        result = self.verifier.verify(signed)
        self.store.add(signed, result.accepted, result.reason)
        return signed, result

    def verify_external(self, event: dict[str, Any]) -> VerificationResult:
        result = self.verifier.verify(event)
        self.store.add(event, result.accepted, result.reason)
        return result
