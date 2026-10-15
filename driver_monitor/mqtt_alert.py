from __future__ import annotations

import threading
import time
import uuid


class MqttAlert:
    """Publish alert states to the Wokwi ESP32 and wait for its MQTT ACK."""

    def __init__(
        self,
        host: str | None,
        port: int = 1883,
        topic_prefix: str = "driver/LAPTOP-CAM-01",
    ) -> None:
        self.host = host
        self.port = port
        self.command_topic = f"{topic_prefix}/command"
        self.ack_topic = f"{topic_prefix}/ack"
        self._client = None
        self._connected = threading.Event()
        self._ack_received = threading.Event()
        self._expected_ack = ""
        self._last_ack_at = 0.0
        self._next_retry_at = 0.0
        self._reported_unavailable = False
        self._async_lock = threading.Lock()
        self._pending_state: str | None = None
        self._async_worker: threading.Thread | None = None

    @property
    def connected(self) -> bool:
        return self._connected.is_set()

    @property
    def device_online(self) -> bool:
        return self.connected and time.monotonic() - self._last_ack_at <= 10.0

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code == 0:
            client.subscribe(self.ack_topic, qos=1)
            self._connected.set()
            print(f"MQTT connected: {self.host}:{self.port}")
        else:
            print(f"MQTT connection rejected: {reason_code}")

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties) -> None:
        self._connected.clear()

    def _on_message(self, client, userdata, message) -> None:
        text = message.payload.decode("utf-8", errors="replace").strip()
        print(f"ESP32 MQTT -> {text}")
        if text == self._expected_ack:
            self._last_ack_at = time.monotonic()
            self._ack_received.set()

    def _connect(self) -> bool:
        if not self.host:
            return False
        if self._client is not None and self._connected.is_set():
            return True
        now = time.monotonic()
        if now < self._next_retry_at:
            return False
        self._next_retry_at = now + 2.0
        try:
            import paho.mqtt.client as mqtt

            self.close()
            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                client_id=f"camera-{uuid.uuid4().hex[:8]}",
                protocol=mqtt.MQTTv311,
            )
            client.on_connect = self._on_connect
            client.on_disconnect = self._on_disconnect
            client.on_message = self._on_message
            self._client = client
            client.connect(self.host, self.port, keepalive=30)
            client.loop_start()
            if not self._connected.wait(2.0):
                raise TimeoutError("broker did not complete the MQTT handshake")
            self._reported_unavailable = False
            return True
        except Exception as error:
            self.close()
            if not self._reported_unavailable:
                print(f"MQTT unavailable ({self.host}:{self.port}): {error}")
                print("Camera continues; start the MQTT broker and Wokwi for ESP32 alerts.")
                self._reported_unavailable = True
            return False

    def send(self, state: str) -> bool:
        if not self._connect():
            return False
        request_id = uuid.uuid4().hex[:8]
        payload = f"{request_id}|{state}"
        self._expected_ack = f"{request_id}|ACK STATE={state}"
        self._ack_received.clear()
        try:
            print(f"ESP32 MQTT <- {state} ({request_id})")
            info = self._client.publish(self.command_topic, payload, qos=1)
            info.wait_for_publish(timeout=2.0)
            if self._ack_received.wait(2.0):
                return True
            print("ESP32 MQTT did not ACK; check that Wokwi is running.")
            return False
        except Exception as error:
            print(f"MQTT publish failed: {error}")
            self.close()
            return False

    def send_async(self, state: str) -> None:
        """Queue the latest alert without blocking the camera processing loop."""
        with self._async_lock:
            self._pending_state = state
            if self._async_worker is not None and self._async_worker.is_alive():
                return
            self._async_worker = threading.Thread(
                target=self._drain_pending_states,
                name="mqtt-alert",
                daemon=True,
            )
            self._async_worker.start()

    def _drain_pending_states(self) -> None:
        while True:
            with self._async_lock:
                state = self._pending_state
                self._pending_state = None
                if state is None:
                    self._async_worker = None
                    return
            self.send(state)

    def close(self) -> None:
        client = self._client
        self._client = None
        self._connected.clear()
        if client is not None:
            try:
                client.disconnect()
                client.loop_stop()
            except BaseException:
                pass
