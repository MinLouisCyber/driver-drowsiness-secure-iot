"""Temporary ESP32 MQTT responder used for an end-to-end laptop test."""

from __future__ import annotations

import threading

import paho.mqtt.client as mqtt

COMMAND_TOPIC = "driver/LAPTOP-CAM-01/command"
ACK_TOPIC = "driver/LAPTOP-CAM-01/ack"


def main() -> None:
    completed = threading.Event()
    count = 0

    def on_connect(client, userdata, flags, reason_code, properties):
        client.subscribe(COMMAND_TOPIC, qos=1)

    def on_message(client, userdata, message):
        nonlocal count
        request_id, state = message.payload.decode().split("|", 1)
        client.publish(ACK_TOPIC, f"{request_id}|ACK STATE={state}", qos=1)
        count += 1
        if count >= 4:
            completed.set()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="mock-esp32")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("127.0.0.1", 1883)
    client.loop_start()
    completed.wait(20)
    client.disconnect()
    client.loop_stop()


if __name__ == "__main__":
    main()
