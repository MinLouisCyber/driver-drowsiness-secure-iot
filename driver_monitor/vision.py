from __future__ import annotations

import math
import time
import urllib.request
from pathlib import Path

from .alarm import Alarm
from .events import EventPipeline
from .mqtt_alert import MqttAlert
from .state import AlertLevel, DrowsinessEngine

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)

RIGHT_EYE = (33, 160, 158, 133, 153, 144)
LEFT_EYE = (362, 385, 387, 263, 373, 380)
MOUTH = (13, 14, 78, 308)


def ensure_model(path: str | Path) -> Path:
    target = Path(path)
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading MediaPipe model to {target} ...")
    urllib.request.urlretrieve(MODEL_URL, target)
    return target


def _point(landmarks, index: int, width: int, height: int) -> tuple[float, float]:
    item = landmarks[index]
    return item.x * width, item.y * height


def eye_aspect_ratio(landmarks, indices, width: int, height: int) -> float:
    points = [_point(landmarks, index, width, height) for index in indices]
    horizontal = math.dist(points[0], points[3])
    if horizontal < 1e-6:
        return 0.0
    vertical = math.dist(points[1], points[5]) + math.dist(points[2], points[4])
    return vertical / (2.0 * horizontal)


def mouth_aspect_ratio(landmarks, width: int, height: int) -> float:
    upper, lower, left, right = [
        _point(landmarks, index, width, height) for index in MOUTH
    ]
    mouth_width = math.dist(left, right)
    return math.dist(upper, lower) / mouth_width if mouth_width > 1e-6 else 0.0


def run_camera(
    camera_index: int,
    model_path: str | Path,
    pipeline: EventPipeline,
    *,
    camera_backend: str = "msmf",
    calibration_seconds: float = 4.0,
    mqtt_host: str | None = None,
    mqtt_port: int = 1883,
    show_preview: bool = True,
    local_alarm: bool = False,
) -> None:
    import cv2
    import mediapipe as mp
    import numpy as np
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    model = ensure_model(model_path)
    options = vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model)),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=1,
    )
    backend_map = {
        "msmf": cv2.CAP_MSMF,
        "dshow": cv2.CAP_DSHOW,
        "auto": cv2.CAP_ANY,
    }
    backend = backend_map.get(camera_backend, cv2.CAP_MSMF)
    capture = cv2.VideoCapture(camera_index, backend)
    if not capture.isOpened():
        raise RuntimeError(
            f"Cannot open USB camera index {camera_index} with backend {camera_backend}"
        )
    print(
        f"Camera opened: index={camera_index}, backend={camera_backend}, "
        f"resolution={int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))}x"
        f"{int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))}"
    )

    engine = DrowsinessEngine()
    alarm = Alarm(pin=18) if local_alarm else None
    mqtt_alert = MqttAlert(mqtt_host, mqtt_port)
    calibration_values: list[float] = []
    calibration_started = time.monotonic()
    ear_threshold: float | None = None
    last_status: AlertLevel | None = None
    last_event_at = 0.0

    quit_hint = "Press q to quit." if show_preview else "Press Ctrl+C to quit."
    print(f"Keep eyes open during calibration. {quit_hint}")
    try:
        with vision.FaceLandmarker.create_from_options(options) as detector:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                frame = cv2.flip(frame, 1)
                height, width = frame.shape[:2]
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = detector.detect(
                    mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                )
                now = time.monotonic()
                face_detected = bool(result.face_landmarks)
                ear_value = mar_value = None
                if face_detected:
                    landmarks = result.face_landmarks[0]
                    ear_value = float(
                        np.mean(
                            [
                                eye_aspect_ratio(landmarks, RIGHT_EYE, width, height),
                                eye_aspect_ratio(landmarks, LEFT_EYE, width, height),
                            ]
                        )
                    )
                    mar_value = mouth_aspect_ratio(landmarks, width, height)

                elapsed = now - calibration_started
                if ear_threshold is None:
                    if ear_value is not None:
                        calibration_values.append(ear_value)
                    remaining = max(0.0, calibration_seconds - elapsed)
                    message = f"CALIBRATING - keep eyes open ({remaining:.1f}s)"
                    if elapsed >= calibration_seconds:
                        if len(calibration_values) < 15:
                            calibration_started = now
                            calibration_values.clear()
                            message = "Face not stable - restarting calibration"
                        else:
                            baseline = float(np.percentile(calibration_values, 75))
                            ear_threshold = baseline * 0.72
                            print(
                                f"Calibration complete: baseline={baseline:.3f}, "
                                f"threshold={ear_threshold:.3f}"
                            )
                    state = None
                else:
                    state = engine.update(
                        now,
                        face_detected=face_detected,
                        ear=ear_value,
                        mar=mar_value,
                        ear_threshold=ear_threshold,
                    )
                    if alarm is not None:
                        alarm.set(state.level is AlertLevel.DROWSY)
                    message = (
                        f"{state.level.value}  EAR={ear_value or 0:.3f}  "
                        f"MAR={mar_value or 0:.3f}  PERCLOS={state.perclos:.0%}"
                    )
                    if state.level != last_status or now - last_event_at >= 5.0:
                        event, verified = pipeline.publish_state(state)
                        print(
                            f"event #{event['sequence']}: {event['status']} "
                            f"({verified.reason})"
                        )
                        mqtt_alert.send(
                            event["status"] if verified.accepted else "TAMPER"
                        )
                        last_status = state.level
                        last_event_at = now

                color = (0, 0, 255) if state and state.level is AlertLevel.DROWSY else (0, 200, 0)
                cv2.rectangle(frame, (0, 0), (width, 45), (0, 0, 0), -1)
                cv2.putText(frame, message, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.62, color, 2)
                if show_preview:
                    cv2.imshow("Secure Driver Drowsiness Monitor", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
    except KeyboardInterrupt:
        print("\nCamera monitoring stopped.")
    finally:
        try:
            if alarm is not None:
                alarm.close()
        except BaseException:
            pass
        mqtt_alert.close()
        try:
            capture.release()
            cv2.destroyAllWindows()
        except BaseException:
            pass
