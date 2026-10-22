"""Wear detection for Genial T31 battery-saving disconnects."""

from datetime import datetime


class WearMonitor:
    """Confirm an unworn probe and shorten later reconnect checks."""

    def __init__(
        self,
        threshold_celsius: float,
        confirm_seconds: int,
        recheck_seconds: int,
    ) -> None:
        self._threshold = threshold_celsius
        self._confirm_seconds = confirm_seconds
        self._recheck_seconds = recheck_seconds
        self._below_since: datetime | None = None
        self._recheck_mode = False
        self.worn: bool | None = None

    def begin_connection(self) -> None:
        """Begin a new observation window without losing confirmed state."""
        self._below_since = None

    def update(
        self, now: datetime, temperature_celsius: float
    ) -> tuple[bool | None, bool]:
        """Return current worn state and whether BLE should disconnect."""
        if temperature_celsius >= self._threshold:
            self._below_since = None
            self._recheck_mode = False
            self.worn = True
            return self.worn, False

        if self._below_since is None:
            self._below_since = now

        required_seconds = (
            self._recheck_seconds if self._recheck_mode else self._confirm_seconds
        )
        if (now - self._below_since).total_seconds() >= required_seconds:
            self.worn = False
            self._recheck_mode = True
            return self.worn, True
        return self.worn, False

