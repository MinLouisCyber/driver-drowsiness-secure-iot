import unittest
import tempfile
from pathlib import Path

from driver_monitor.runtime import MonitorRuntime
from driver_monitor.web import create_app, format_timestamp, present_events


class WebTimestampTests(unittest.TestCase):
    def test_unix_timestamp_is_displayed_in_vietnam_time(self):
        self.assertEqual("08/10/2026 16:54:57", format_timestamp(1_791_453_297))

    def test_raw_timestamp_is_preserved_for_api_clients(self):
        events = present_events([{"timestamp": 1_791_453_297, "status": "NORMAL"}])
        self.assertEqual(1_791_453_297, events[0]["timestamp"])
        self.assertEqual("08/10/2026 16:54:57", events[0]["timestamp_display"])

    def test_invalid_timestamp_has_safe_label(self):
        self.assertEqual("Unknown", format_timestamp("invalid"))

    def test_live_status_endpoint_uses_camera_runtime(self):
        runtime = MonitorRuntime()
        runtime.update_status(camera="ACTIVE", level="NORMAL", ear=0.291)
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Path(directory) / "events.db", runtime)
            response = app.test_client().get("/api/status")
        self.assertEqual(200, response.status_code)
        self.assertEqual("ACTIVE", response.json["camera"])
        self.assertEqual("NORMAL", response.json["level"])
        self.assertEqual(0.291, response.json["ear"])

    def test_dashboard_without_runtime_reports_offline(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Path(directory) / "events.db")
            response = app.test_client().get("/api/status")
        self.assertEqual("OFFLINE", response.json["camera"])

    def test_each_dashboard_tab_has_its_own_route(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Path(directory) / "events.db")
            client = app.test_client()
            pages = {
                "/": b"Driver Overview",
                "/live": b"Live Monitor",
                "/events": b"Event History",
                "/security": b"Data Security",
            }
            for route, title in pages.items():
                with self.subTest(route=route):
                    response = client.get(route)
                    self.assertEqual(200, response.status_code)
                    self.assertIn(title, response.data)

    def test_events_page_has_fixed_columns_and_pagination(self):
        with tempfile.TemporaryDirectory() as directory:
            app = create_app(Path(directory) / "events.db")
            response = app.test_client().get("/events")
        self.assertEqual(200, response.status_code)
        self.assertIn(b"<colgroup>", response.data)
        self.assertIn(b'id="events-pages"', response.data)
        self.assertIn(b'id="events-prev"', response.data)
        self.assertIn(b'id="events-next"', response.data)


if __name__ == "__main__":
    unittest.main()
