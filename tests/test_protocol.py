"""Tests for the Genial T31 wire protocol."""

from datetime import datetime
import importlib.util
from pathlib import Path
import sys
import unittest

MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "genial_t31"
    / "protocol.py"
)
SPEC = importlib.util.spec_from_file_location("genial_protocol", MODULE_PATH)
assert SPEC and SPEC.loader
protocol = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = protocol
SPEC.loader.exec_module(protocol)


class ProtocolTests(unittest.TestCase):
    """Verify framing and captured Genial payloads."""

    def test_official_commands(self) -> None:
        self.assertEqual(protocol.connect_command().hex(), "a602a500a76a")
        self.assertEqual(protocol.settings_command().hex(), "a6021d001f6a")
        self.assertEqual(protocol.battery_command().hex(), "a602b100b36a")

    def test_dynamic_time_command(self) -> None:
        # Tuesday maps to JavaScript/Tempal weekday 2.
        value = protocol.sync_time_command(datetime(2026, 10, 20, 21, 34, 56))
        self.assertEqual(value.hex(), "a6053702152238ad6a")

    def test_captured_temperature(self) -> None:
        frame = protocol.parse_frame(bytes.fromhex("a609010e4e0d9803071a02316a"))
        reading = protocol.decode_temperature(frame.body)
        self.assertEqual(reading.temperature_celsius, 36.62)
        self.assertEqual(reading.auxiliary_temperature_celsius, 34.80)
        self.assertEqual((reading.weekday, reading.hour, reading.minute, reading.second), (3, 7, 26, 2))

    def test_captured_battery(self) -> None:
        frame = protocol.parse_frame(bytes.fromhex("a605b104640136556a"))
        reading = protocol.decode_battery(frame.body)
        self.assertEqual(reading.level, 4)
        self.assertEqual(reading.percent, 100)
        self.assertEqual(reading.voltage_mv, 3100)

    def test_rejects_bad_checksum(self) -> None:
        with self.assertRaises(protocol.ProtocolError):
            protocol.parse_frame(bytes.fromhex("a602a500006a"))

    def test_fragmented_frames(self) -> None:
        buffer = bytearray(bytes.fromhex("00ffa609010e4e0d98"))
        self.assertEqual(protocol.extract_frames(buffer), [])
        buffer.extend(bytes.fromhex("03071a02316a"))
        frames = protocol.extract_frames(buffer)
        self.assertEqual(len(frames), 1)
        self.assertEqual(frames[0].command, protocol.COMMAND_TEMPERATURE)
        self.assertEqual(buffer, bytearray())


if __name__ == "__main__":
    unittest.main()

