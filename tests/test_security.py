import copy
import unittest

from driver_monitor.security import EventSigner, EventVerifier


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.signer = EventSigner("CAM-01", "secret")
        self.verifier = EventVerifier({"CAM-01": "secret"}, max_age_seconds=60)
        self.event = {
            "timestamp": 1_700_000_000,
            "sequence": 1,
            "status": "DROWSY",
            "ear": 0.12,
        }

    def test_valid_event_is_accepted(self):
        signed = self.signer.sign(self.event)
        result = self.verifier.verify(signed, now=1_700_000_001)
        self.assertTrue(result.accepted)

    def test_modified_event_is_rejected(self):
        signed = self.signer.sign(self.event)
        signed["status"] = "NORMAL"
        result = self.verifier.verify(signed, now=1_700_000_001)
        self.assertFalse(result.accepted)
        self.assertIn("modified", result.reason)

    def test_replay_is_rejected(self):
        signed = self.signer.sign(self.event)
        self.assertTrue(self.verifier.verify(signed, now=1_700_000_001).accepted)
        result = self.verifier.verify(copy.deepcopy(signed), now=1_700_000_002)
        self.assertFalse(result.accepted)
        self.assertIn("replayed", result.reason)

    def test_unknown_device_is_rejected(self):
        signed = EventSigner("UNKNOWN", "other").sign(self.event)
        result = self.verifier.verify(signed, now=1_700_000_001)
        self.assertFalse(result.accepted)
        self.assertEqual("unknown device", result.reason)


if __name__ == "__main__":
    unittest.main()

