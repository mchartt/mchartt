"""Regression tests for the profile contribution renderer (offline)."""
from datetime import date, timedelta
import unittest

from scripts.render_activity import CalendarParser, calendar_days, stats, render_snake, snake_route
from scripts.render_terminal import render as render_terminal
import xml.etree.ElementTree as ET


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


    def test_random_routes_collect_all_active_cells(self):
        start = date(2026, 1, 1)
        days = [(start + timedelta(days=i), 1 if i % 5 == 0 else 0)
                for i in range(365)]
        offset = (days[0][0].weekday() + 1) % 7
        cells = {divmod(offset+i, 7): day for i, day in enumerate(days)}
        route_a = snake_route(cells, "first-refresh")
        route_b = snake_route(cells, "second-refresh")
        self.assertNotEqual(route_a, route_b)
        self.assertEqual(route_a[0], route_a[-1])
        self.assertTrue({cell for cell, (_, n) in cells.items() if n > 0}.issubset(route_a))
        for a, b in zip(route_a, route_a[1:]):
            self.assertEqual(abs(a[0]-b[0]) + abs(a[1]-b[1]), 1)

    def test_snake_head_leads_tail(self):
        start = date(2026, 1, 1)
        days = [(start + timedelta(days=i), i % 4 == 0 and 2 or 0)
                for i in range(70)]
        svg = render_snake(days, "dark", seed="stable-test")
        self.assertIn('class="snake-face"', svg)
        self.assertIn('cx="8.2"', svg)
        self.assertIn('animation-delay:0.00000s', svg)
        self.assertIn('Randomized contribution snake', svg)
        self.assertEqual(svg.count('class="snake-segment"'), 9)

    def test_ascii_terminal_is_valid_and_theme_aware(self):
        dark, light = render_terminal("dark"), render_terminal("light")
        self.assertNotEqual(dark, light)
        self.assertEqual(
            ET.fromstring(dark).tag,
            "{http://www.w3.org/2000/svg}svg")
        self.assertIn('ASCII SIGNATURE', dark)
        self.assertIn('prefers-reduced-motion:reduce', dark)
        self.assertIn('SOFTWARE', dark)

    def test_reduced_motion_preserves_static_snake(self):
        start = date(2026, 1, 1)
        days = [(start + timedelta(days=i), 1) for i in range(14)]
        svg = render_snake(days, "dark")
        self.assertIn("@media(prefers-reduced-motion:reduce)", svg)
        self.assertIn("animation:none!important", svg)
        self.assertNotIn(".segment{display:none}", svg)


if __name__ == "__main__":
    unittest.main()
