from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any


def canonical_bytes(event: dict[str, Any]) -> bytes:
    unsigned = {key: value for key, value in event.items() if key != "signature"}
    return json.dumps(
        unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


class EventSigner:
    def __init__(self, device_id: str, secret: str) -> None:
        if not device_id or not secret:
            raise ValueError("device_id and secret are required")
        self.device_id = device_id
        self._secret = secret.encode("utf-8")

    def sign(self, event: dict[str, Any]) -> dict[str, Any]:
        signed = dict(event)
        signed["device_id"] = self.device_id
        signed["signature"] = hmac.new(
            self._secret, canonical_bytes(signed), hashlib.sha256
        ).hexdigest()
        return signed


@dataclass(frozen=True)
class VerificationResult:
    accepted: bool
    reason: str


class EventVerifier:
    """Verifies source, integrity, freshness and replay protection."""

    def __init__(self, device_secrets: dict[str, str], max_age_seconds: int = 86400) -> None:
        self._secrets = {key: value.encode("utf-8") for key, value in device_secrets.items()}
        self._max_age = max_age_seconds
        self._highest_sequence: dict[str, int] = {}

    def verify(self, event: dict[str, Any], now: int | None = None) -> VerificationResult:
        now = int(time.time()) if now is None else int(now)
        device_id = str(event.get("device_id", ""))
        if device_id not in self._secrets:
            return VerificationResult(False, "unknown device")

        signature = str(event.get("signature", ""))
        expected = hmac.new(
            self._secrets[device_id], canonical_bytes(event), hashlib.sha256
        ).hexdigest()
        if not signature or not hmac.compare_digest(signature, expected):
            return VerificationResult(False, "invalid signature: data was modified")

        try:
            timestamp = int(event["timestamp"])
            sequence = int(event["sequence"])
        except (KeyError, TypeError, ValueError):
            return VerificationResult(False, "invalid timestamp or sequence")

        if abs(now - timestamp) > self._max_age:
            return VerificationResult(False, "stale timestamp")

        highest = self._highest_sequence.get(device_id, -1)
        if sequence <= highest:
            return VerificationResult(False, "replayed or out-of-order sequence")

        self._highest_sequence[device_id] = sequence
        return VerificationResult(True, "verified")

