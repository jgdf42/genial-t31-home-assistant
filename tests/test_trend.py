"""Tests for false-positive-resistant temperature trends."""

from datetime import UTC, datetime, timedelta
import importlib.util
from pathlib import Path
import sys
import unittest

MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "genial_t31"
    / "trend.py"
)
SPEC = importlib.util.spec_from_file_location("genial_trend", MODULE_PATH)
assert SPEC and SPEC.loader
trend_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = trend_module
SPEC.loader.exec_module(trend_module)


class TemperatureTrendTests(unittest.TestCase):
    """Verify warm-up gating and rolling calculations."""

    def test_off_body_reading_has_no_trend(self) -> None:
        trend = trend_module.TemperatureTrend()
        now = datetime(2026, 1, 1, tzinfo=UTC)
        self.assertEqual(trend.update(now, 35.0), (None, None, None))

    def test_baseline_requires_five_minutes(self) -> None:
        trend = trend_module.TemperatureTrend()
        start = datetime(2026, 1, 1, tzinfo=UTC)
        for minute in range(5):
            baseline, rise, _rate = trend.update(
                start + timedelta(minutes=minute), 36.5
            )
            self.assertIsNone(baseline)
            self.assertIsNone(rise)

        baseline, rise, rate = trend.update(start + timedelta(minutes=5), 36.8)
        self.assertEqual(baseline, 36.5)
        self.assertAlmostEqual(rise, 0.3)
        self.assertAlmostEqual(rate, 0.15)

    def test_off_body_value_resets_worn_session(self) -> None:
        trend = trend_module.TemperatureTrend()
        start = datetime(2026, 1, 1, tzinfo=UTC)
        trend.update(start, 36.5)
        trend.update(start + timedelta(minutes=5), 36.5)
        self.assertEqual(
            trend.update(start + timedelta(minutes=6), 35.0),
            (None, None, None),
        )
        self.assertEqual(
            trend.update(start + timedelta(minutes=7), 36.6),
            (None, None, None),
        )


if __name__ == "__main__":
    unittest.main()

