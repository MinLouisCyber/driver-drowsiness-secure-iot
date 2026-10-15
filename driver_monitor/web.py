from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .runtime import MonitorRuntime
from .storage import EventStore

VIETNAM_TIMEZONE = timezone(timedelta(hours=7))


def format_timestamp(value: int | float | str) -> str:
    try:
        moment = datetime.fromtimestamp(float(value), tz=VIETNAM_TIMEZONE)
    except (TypeError, ValueError, OSError):
        return "Unknown"
    return moment.strftime("%d/%m/%Y %H:%M:%S")


def _payload(event: dict) -> dict:
    try:
        return json.loads(event.get("payload", "{}"))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def _event_reason(event: dict) -> str:
    reason = str(event.get("verification_reason", ""))
    if event.get("accepted"):
        reasons = _payload(event).get("reasons", [])
        if reasons:
            return ", ".join(reasons)
        return {
            "NORMAL": "Metrics within the safe range",
            "WARNING": "Early fatigue indicators detected",
            "DROWSY": "Prolonged eye closure or missing face",
        }.get(str(event.get("status")), "Verified telemetry")
    lowered = reason.lower()
    if "signature" in lowered:
        return "Invalid HMAC signature"
    if "replay" in lowered or "out-of-order" in lowered:
        return "Replay or out-of-order packet"
    if "unknown device" in lowered:
        return "Unregistered device"
    if "stale" in lowered:
        return "Expired timestamp"
    return reason


def present_events(events: list[dict]) -> list[dict]:
    return [
        {
            **event,
            "timestamp_display": format_timestamp(event.get("timestamp", 0)),
            "display_reason": _event_reason(event),
        }
        for event in events
    ]


def present_analytics(events: list[dict]) -> list[dict]:
    points = []
    for event in reversed(events):
        payload = _payload(event)
        if not event.get("accepted") or not payload:
            continue
        points.append(
            {
                "timestamp": event["timestamp"],
                "time": datetime.fromtimestamp(
                    event["timestamp"], tz=VIETNAM_TIMEZONE
                ).strftime("%H:%M:%S"),
                "status": event["status"],
                "ear": payload.get("ear"),
                "mar": payload.get("mar"),
                "perclos": payload.get("perclos", 0),
                "yawns": payload.get("yawns", 0),
            }
        )
    return points


def create_app(database: str | Path, runtime: MonitorRuntime | None = None):
    from flask import Flask, Response, jsonify, render_template

    app = Flask(__name__)
    store = EventStore(database)

    def page_context(active_page: str, title: str, subtitle: str) -> dict:
        return {
            "active_page": active_page,
            "page_title": title,
            "page_subtitle": subtitle,
            "live_camera": runtime is not None,
        }

    @app.get("/")
    def overview():
        return render_template(
            "overview.html",
            **page_context(
                "overview",
                "Driver Overview",
                "Fatigue trends and current driver state",
            ),
        )

    @app.get("/live")
    def live():
        return render_template(
            "live.html",
            **page_context(
                "live",
                "Live Monitor",
                "Real-time camera and facial telemetry",
            ),
        )

    @app.get("/events")
    def event_page():
        return render_template(
            "events.html",
            **page_context(
                "events",
                "Event History",
                "Review fatigue alerts and system decisions",
            ),
        )

    @app.get("/security")
    def security():
        return render_template(
            "security.html",
            **page_context(
                "security",
                "Data Security",
                "HMAC integrity and replay-attack monitoring",
            ),
        )

    @app.get("/api/events")
    def events_api():
        return jsonify(present_events(store.latest(100)))

    @app.get("/api/analytics")
    def analytics_api():
        return jsonify(present_analytics(store.latest(200)))

    @app.get("/api/status")
    def status_api():
        if runtime is None:
            data = {
                "camera": "OFFLINE",
                "mqtt": "DISCONNECTED",
                "esp32": "WAITING",
                "level": "OFFLINE",
                "message": "Camera is not running in this dashboard process",
            }
        else:
            data = runtime.status()
        latest = store.latest(1)
        data["tamper"] = bool(
            latest
            and not latest[0]["accepted"]
            and int(time.time()) - int(latest[0]["timestamp"]) <= 10
        )
        return jsonify(data)

    @app.get("/video-feed")
    def video_feed():
        if runtime is None:
            return Response(status=404)

        def frames():
            version = -1
            while True:
                version, jpeg = runtime.wait_for_frame(version)
                if jpeg is not None:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"

        return Response(frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

    return app
