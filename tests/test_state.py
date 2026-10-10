import unittest

from driver_monitor.state import AlertLevel, DrowsinessEngine


class DrowsinessEngineTests(unittest.TestCase):
    def test_normal_open_eyes(self):
        engine = DrowsinessEngine()
        state = engine.update(
            0.0, face_detected=True, ear=0.30, mar=0.2, ear_threshold=0.20
        )
        self.assertEqual(AlertLevel.NORMAL, state.level)

    def test_long_eye_closure_triggers_alarm(self):
        engine = DrowsinessEngine()
        engine.update(0.0, face_detected=True, ear=0.10, mar=0.2, ear_threshold=0.20)
        state = engine.update(
            1.6, face_detected=True, ear=0.10, mar=0.2, ear_threshold=0.20
        )
        self.assertEqual(AlertLevel.DROWSY, state.level)

    def test_missing_face_triggers_alarm(self):
        engine = DrowsinessEngine()
        engine.update(
            0.0, face_detected=False, ear=None, mar=None, ear_threshold=0.20
        )
        state = engine.update(
            2.1, face_detected=False, ear=None, mar=None, ear_threshold=0.20
        )
        self.assertEqual(AlertLevel.DROWSY, state.level)

    def test_opening_eyes_releases_alarm_with_high_perclos(self):
        engine = DrowsinessEngine()
        for second in range(11):
            engine.update(
                float(second),
                face_detected=True,
                ear=0.30,
                mar=0.2,
                ear_threshold=0.20,
            )
        for second in range(11, 18):
            state = engine.update(
                float(second),
                face_detected=True,
                ear=0.10,
                mar=0.2,
                ear_threshold=0.20,
            )
        self.assertEqual(AlertLevel.DROWSY, state.level)

        recovered = engine.update(
            18.0,
            face_detected=True,
            ear=0.30,
            mar=0.2,
            ear_threshold=0.20,
        )
        self.assertGreaterEqual(recovered.perclos, 0.35)
        self.assertEqual(AlertLevel.WARNING, recovered.level)


if __name__ == "__main__":
    unittest.main()

