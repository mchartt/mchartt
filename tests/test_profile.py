"""Regression tests for the profile contribution renderer (offline)."""
from datetime import date, timedelta
import unittest

from scripts.render_activity import CalendarParser, calendar_days, stats, render_snake


class ProfileTests(unittest.TestCase):
    def test_current_streak_can_end_yesterday(self):
        start = date(2026, 1, 1)
        days = [(start + timedelta(days=i), count)
                for i, count in enumerate([0, 1, 1, 1, 0])]
        self.assertEqual(stats(days), (3, 3, 3, 3))

    def test_current_streak_ends_after_gap(self):
        start = date(2026, 1, 1)
        days = [(start + timedelta(days=i), count)
                for i, count in enumerate([1, 1, 0, 0])]
        self.assertEqual(stats(days), (2, 2, 0, 2))

    def test_calendar_rejects_missing_days(self):
        with self.assertRaises(ValueError):
            calendar_days({"2026-01-01": 1}, date(2026, 1, 1))

    def test_calendar_rejects_negative_counts(self):
        today = date(2026, 11, 20)
        values = {(today - timedelta(days=i)).isoformat(): 0 for i in range(365)}
        values[today.isoformat()] = -1
        with self.assertRaises(ValueError):
            calendar_days(values, today)

    def test_tooltip_and_legacy_count_formats(self):
        parser = CalendarParser()
        parser.feed(
            '<td data-date="2026-11-19" id="a"></td>'
            '<tool-tip for="a">1,234 contributions on Nov 19, 2026</tool-tip>'
            '<td data-date="2026-11-20" data-count="5"></td>'
            '<td data-date="2026-11-18" id="b"></td>'
            '<tool-tip for="b">No contributions on Nov 18, 2026</tool-tip>'
        )
        self.assertEqual(parser.counts(), {
            "2026-11-19": 1234, "2026-11-20": 5, "2026-11-18": 0
        })

    def test_reduced_motion_preserves_static_snake(self):
        start = date(2026, 1, 1)
        days = [(start + timedelta(days=i), 1) for i in range(14)]
        svg = render_snake(days, "dark")
        self.assertIn("@media(prefers-reduced-motion:reduce)", svg)
        self.assertIn("animation:none!important", svg)
        self.assertNotIn(".segment{display:none}", svg)


if __name__ == "__main__":
    unittest.main()
