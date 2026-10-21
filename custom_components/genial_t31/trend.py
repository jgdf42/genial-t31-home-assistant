"""Temperature trend calculations for the Genial T31."""

from collections import deque
from datetime import datetime
from statistics import median


class TemperatureTrend:
    """Track on-body history and calculate stable trend values."""

    def __init__(self) -> None:
        self._history: deque[tuple[datetime, float]] = deque()
        self._on_body_since: datetime | None = None

    def update(
        self, now: datetime, temperature_celsius: float
    ) -> tuple[float | None, float | None, float | None]:
        """Return baseline, rise, and two-minute rate in Celsius units."""
        if temperature_celsius >= 36.1111:  # 97 F
            if self._on_body_since is None:
                self._on_body_since = now
        elif temperature_celsius < 35.8333:  # 96.5 F
            self._on_body_since = None
            self._history.clear()
            return None, None, None

        if self._on_body_since is None or temperature_celsius < 36.1111:
            return None, None, None

        self._history.append((now, temperature_celsius))
        while self._history and (
            now - self._history[0][0]
        ).total_seconds() > 900:
            self._history.popleft()

        baseline_samples = [
            value
            for timestamp, value in self._history
            if 300 <= (now - timestamp).total_seconds() <= 900
        ]
        baseline = median(baseline_samples) if baseline_samples else None
        rise = temperature_celsius - baseline if baseline is not None else None

        recent = [
            sample
            for sample in self._history
            if (now - sample[0]).total_seconds() <= 120
        ]
        rate = None
        if recent:
            elapsed_seconds = (now - recent[0][0]).total_seconds()
            if elapsed_seconds >= 60:
                rate = (temperature_celsius - recent[0][1]) * 60 / elapsed_seconds
        return baseline, rise, rate

