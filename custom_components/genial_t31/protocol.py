"""Framing and payload decoding for the Genial T31 BLE protocol."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

START_OF_PACKET = 0xA6
END_OF_PACKET = 0x6A

COMMAND_TEMPERATURE = 0x01
COMMAND_SETTINGS = 0x1D
COMMAND_SYNC_TIME = 0x37
COMMAND_SYNC_REQUEST = 0x38
COMMAND_CONNECT_RESPONSE = 0x5A
COMMAND_CONNECT = 0xA5
COMMAND_BATTERY = 0xB1


class ProtocolError(ValueError):
    """Raised when a T31 packet is malformed."""


@dataclass(frozen=True, slots=True)
class T31Frame:
    """A validated T31 frame."""

    command: int
    body: bytes


@dataclass(frozen=True, slots=True)
class TemperatureReading:
    """Decoded command-01 telemetry."""

    temperature_celsius: float
    auxiliary_temperature_celsius: float
    weekday: int
    hour: int
    minute: int
    second: int


@dataclass(frozen=True, slots=True)
class BatteryReading:
    """Decoded command-B1 battery telemetry."""

    level: int
    percent: int
    voltage_mv: int


def build_frame(command: int, body: bytes = b"") -> bytes:
    """Build a framed command with the protocol checksum."""
    if not 0 <= command <= 0xFF:
        raise ProtocolError("Command must fit in one byte")
    payload_length = 1 + len(body)
    if payload_length > 0xFF:
        raise ProtocolError("Payload is too long")
    checksum = (payload_length + command + sum(body)) & 0xFF
    return bytes((START_OF_PACKET, payload_length, command)) + body + bytes(
        (checksum, END_OF_PACKET)
    )


def parse_frame(packet: bytes) -> T31Frame:
    """Validate and parse one complete T31 frame."""
    if len(packet) < 5:
        raise ProtocolError("Frame is too short")
    if packet[0] != START_OF_PACKET or packet[-1] != END_OF_PACKET:
        raise ProtocolError("Invalid frame markers")
    expected_length = packet[1] + 4
    if len(packet) != expected_length:
        raise ProtocolError(
            f"Frame length mismatch: expected {expected_length}, got {len(packet)}"
        )
    command = packet[2]
    body = packet[3:-2]
    checksum = (packet[1] + command + sum(body)) & 0xFF
    if packet[-2] != checksum:
        raise ProtocolError("Invalid checksum")
    return T31Frame(command, body)


def extract_frames(buffer: bytearray) -> list[T31Frame]:
    """Extract complete frames while tolerating fragments and leading noise."""
    frames: list[T31Frame] = []
    while buffer:
        try:
            start = buffer.index(START_OF_PACKET)
        except ValueError:
            buffer.clear()
            break
        if start:
            del buffer[:start]
        if len(buffer) < 2:
            break
        total_length = buffer[1] + 4
        if len(buffer) < total_length:
            break
        candidate = bytes(buffer[:total_length])
        del buffer[:total_length]
        try:
            frames.append(parse_frame(candidate))
        except ProtocolError:
            continue
    return frames


def decode_temperature(body: bytes) -> TemperatureReading:
    """Decode a plaintext Genial command-01 body."""
    if len(body) != 8:
        raise ProtocolError(f"Expected 8 temperature bytes, got {len(body)}")
    temperature = int.from_bytes(body[0:2], "big") / 100
    auxiliary = int.from_bytes(body[2:4], "big") / 100
    if not 20 <= temperature <= 45 or not 0 <= auxiliary <= 50:
        raise ProtocolError("Temperature is outside the supported range")
    weekday, hour, minute, second = body[4:8]
    if weekday > 6 or hour > 23 or minute > 59 or second > 59:
        raise ProtocolError("Invalid device timestamp")
    return TemperatureReading(
        temperature, auxiliary, weekday, hour, minute, second
    )


def decode_battery(body: bytes) -> BatteryReading:
    """Decode level, percentage, and centivolt fields from command B1."""
    if len(body) != 4:
        raise ProtocolError(f"Expected 4 battery bytes, got {len(body)}")
    percent = body[1]
    if percent > 100:
        raise ProtocolError("Invalid battery percentage")
    return BatteryReading(
        level=body[0],
        percent=percent,
        voltage_mv=int.from_bytes(body[2:4], "big") * 10,
    )


def connect_command() -> bytes:
    """Build the command that starts a Genial session."""
    return build_frame(COMMAND_CONNECT, b"\x00")


def settings_command() -> bytes:
    """Build the official settings acknowledgement/request."""
    return build_frame(COMMAND_SETTINGS, b"\x00")


def battery_command() -> bytes:
    """Request a battery report."""
    return build_frame(COMMAND_BATTERY, b"\x00")


def sync_time_command(now: datetime | None = None) -> bytes:
    """Build the official local-clock synchronization command."""
    current = now or datetime.now().astimezone()
    weekday = (current.weekday() + 1) % 7  # Sunday=0, matching Tempal.
    return build_frame(
        COMMAND_SYNC_TIME,
        bytes((weekday, current.hour, current.minute, current.second)),
    )

