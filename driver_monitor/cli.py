from __future__ import annotations

import argparse
import time
from pathlib import Path

from .events import EventPipeline
from .state import DrowsinessEngine

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "events.db"
DEFAULT_MODEL = ROOT / "models" / "face_landmarker.task"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Secure driver drowsiness monitor")
    commands = parser.add_subparsers(dest="command", required=True)

    simulation = commands.add_parser("simulate", help="run without a camera")
    simulation.add_argument("--database", default=str(DEFAULT_DB))

    camera = commands.add_parser("camera", help="run with a USB camera")
    camera.add_argument("--index", type=int, default=0)
    camera.add_argument(
        "--camera-backend",
        choices=("msmf", "dshow", "auto"),
        default="msmf",
        help="Windows camera backend (default: msmf)",
    )
    camera.add_argument("--model", default=str(DEFAULT_MODEL))
    camera.add_argument("--database", default=str(DEFAULT_DB))
    camera.add_argument(
        "--mqtt-host",
        default=None,
        help="MQTT broker used by the simulated ESP32, e.g. 127.0.0.1",
    )
    camera.add_argument("--mqtt-port", type=int, default=1883)
    camera.add_argument(
        "--no-preview",
        action="store_true",
        help="do not open the OpenCV window (useful while Wokwi must stay visible)",
    )
    mqtt_test = commands.add_parser(
        "mqtt-test", help="test Wokwi LEDs and buzzer over MQTT"
    )
    mqtt_test.add_argument("--mqtt-host", default="127.0.0.1")
    mqtt_test.add_argument("--mqtt-port", type=int, default=1883)

    broker = commands.add_parser("broker", help="run the local MQTT broker")
    broker.add_argument("--host", default="0.0.0.0")
    broker.add_argument("--port", type=int, default=1883)

    server = commands.add_parser("serve", help="open the event dashboard")
    server.add_argument("--database", default=str(DEFAULT_DB))
    server.add_argument("--host", default="127.0.0.1")
    server.add_argument("--port", type=int, default=5000)
    return parser


def run_simulation(database: str) -> None:
    pipeline = EventPipeline(database)
    engine = DrowsinessEngine()
    scenarios = [
        ("normal", 2.0, 0.30, 0.25),
        ("eyes closing", 0.9, 0.12, 0.25),
        ("drowsy", 1.2, 0.10, 0.25),
        ("recovered", 1.0, 0.31, 0.25),
    ]
    latest = None
    for name, duration, ear, mar in scenarios:
        steps = int(duration * 10)
        for _ in range(steps):
            timestamp = time.monotonic()
            latest = engine.update(
                timestamp,
                face_detected=True,
                ear=ear,
                mar=mar,
                ear_threshold=0.20,
            )
            time.sleep(0.1)
        event, result = pipeline.publish_state(latest)
        print(f"{name:14} -> {event['status']:7} | {result.reason}")

    print("\nTamper test:")
    tampered = dict(event)
    tampered["status"] = "NORMAL" if event["status"] != "NORMAL" else "DROWSY"
    tampered["sequence"] += 1
    result = pipeline.verify_external(tampered)
    print(f"modified status -> accepted={result.accepted}, reason={result.reason}")

    replay = dict(event)
    result = pipeline.verify_external(replay)
    print(f"replayed packet -> accepted={result.accepted}, reason={result.reason}")
    print(f"\nDatabase: {database}")


def run_mqtt_test(mqtt_host: str, mqtt_port: int) -> None:
    from .mqtt_alert import MqttAlert

    sender = MqttAlert(mqtt_host, mqtt_port)
    passed = True
    try:
        for state in ("NORMAL", "WARNING", "DROWSY", "NORMAL"):
            print(f"\nTesting {state} ...")
            passed = sender.send(state) and passed
            time.sleep(2.0)
    finally:
        sender.close()
    if not passed:
        raise SystemExit("Wokwi MQTT test FAILED: no ACK from the simulated ESP32")
    print("\nWokwi MQTT test PASSED")


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "simulate":
        run_simulation(args.database)
    elif args.command == "camera":
        from .vision import run_camera

        pipeline = EventPipeline(args.database)
        run_camera(
            args.index,
            args.model,
            pipeline,
            camera_backend=args.camera_backend,
            mqtt_host=args.mqtt_host,
            mqtt_port=args.mqtt_port,
            show_preview=not args.no_preview,
        )
    elif args.command == "mqtt-test":
        run_mqtt_test(args.mqtt_host, args.mqtt_port)
    elif args.command == "broker":
        from .broker import run_broker

        run_broker(args.host, args.port)
    elif args.command == "serve":
        from .web import create_app

        create_app(args.database).run(host=args.host, port=args.port, debug=False)
