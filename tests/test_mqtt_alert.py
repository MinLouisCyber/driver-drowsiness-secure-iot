import types
import unittest
import threading
import time
from unittest.mock import patch

import paho.mqtt.client as mqtt

from driver_monitor.mqtt_alert import MqttAlert


class FakePublishInfo:
    def wait_for_publish(self, timeout=None):
        return True


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.on_connect = None
        self.on_disconnect = None
        self.on_message = None
        self.published = []

    def connect(self, host, port, keepalive):
        self.on_connect(self, None, None, 0, None)

    def loop_start(self):
        pass

    def subscribe(self, topic, qos=0):
        self.subscription = (topic, qos)

    def publish(self, topic, payload, qos=0):
        self.published.append((topic, payload, qos))
        request_id, state = payload.split("|", 1)
        message = types.SimpleNamespace(
            payload=f"{request_id}|ACK STATE={state}".encode()
        )
        self.on_message(self, None, message)
        return FakePublishInfo()

    def disconnect(self):
        pass

    def loop_stop(self):
        pass


class MqttAlertTests(unittest.TestCase):
    def test_publish_and_matching_ack(self):
        with patch.object(mqtt, "Client", FakeClient):
            sender = MqttAlert("127.0.0.1")
            self.assertTrue(sender.send("DROWSY"))
            sender.close()

    def test_async_publish_does_not_block_camera_caller(self):
        sender = MqttAlert(None)
        finished = threading.Event()

        def slow_send(state):
            time.sleep(0.2)
            finished.set()
            return True

        sender.send = slow_send
        started = time.monotonic()
        sender.send_async("DROWSY")
        self.assertLess(time.monotonic() - started, 0.1)
        self.assertTrue(finished.wait(1.0))


if __name__ == "__main__":
    unittest.main()
