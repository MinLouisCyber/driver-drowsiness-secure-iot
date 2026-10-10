import unittest

from driver_monitor.web import format_timestamp, present_events


class WebTimestampTests(unittest.TestCase):
    def test_unix_timestamp_is_displayed_in_vietnam_time(self):
        self.assertEqual("08/10/2026 16:54:57", format_timestamp(1_791_453_297))

    def test_raw_timestamp_is_preserved_for_api_clients(self):
        events = present_events([{"timestamp": 1_791_453_297, "status": "NORMAL"}])
        self.assertEqual(1_791_453_297, events[0]["timestamp"])
        self.assertEqual("08/10/2026 16:54:57", events[0]["timestamp_display"])

    def test_invalid_timestamp_has_safe_label(self):
        self.assertEqual("Không xác định", format_timestamp("invalid"))


if __name__ == "__main__":
    unittest.main()
