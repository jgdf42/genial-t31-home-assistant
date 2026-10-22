"""Tests for unworn power-saving behavior."""

from datetime import UTC, datetime, timedelta
import importlib.util
from pathlib import Path
import sys
import unittest

MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "genial_t31"
    / "wear.py"
)
SPEC = importlib.util.spec_from_file_location("genial_wear", MODULE_PATH)
assert SPEC and SPEC.loader
wear_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = wear_module
SPEC.loader.exec_module(wear_module)


class WearMonitorTests(unittest.TestCase):
    """Verify confirmation, recovery, and short reconnect probes."""

    def setUp(self) -> None:
        self.monitor = wear_module.WearMonitor(31.6667, 600, 60)
        self.start = datetime(2026, 1, 1, tzinfo=UTC)

    def test_low_temperature_requires_ten_minutes(self) -> None:
        self.assertEqual(self.monitor.update(self.start, 25), (None, False))
        self.assertEqual(
            self.monitor.update(self.start + timedelta(seconds=599), 25),
            (None, False),
        )
        self.assertEqual(
            self.monitor.update(self.start + timedelta(seconds=600), 25),
            (False, True),
        )

    def test_warm_temperature_cancels_unworn_timer(self) -> None:
        self.monitor.update(self.start, 25)
        self.assertEqual(
            self.monitor.update(self.start + timedelta(minutes=5), 36.5),
            (True, False),
        )
        self.assertEqual(
            self.monitor.update(self.start + timedelta(minutes=11), 25),
            (True, False),
        )

    def test_recheck_disconnects_after_one_minute(self) -> None:
        self.monitor.update(self.start, 25)
        self.monitor.update(self.start + timedelta(minutes=10), 25)
        self.monitor.begin_connection()
        recheck = self.start + timedelta(minutes=25)
        self.assertEqual(self.monitor.update(recheck, 25), (False, False))
        self.assertEqual(
            self.monitor.update(recheck + timedelta(seconds=60), 25),
            (False, True),
        )
        self.assertEqual(
            self.monitor.update(recheck + timedelta(seconds=61), 36.5),
            (True, False),
        )


if __name__ == "__main__":
    unittest.main()

