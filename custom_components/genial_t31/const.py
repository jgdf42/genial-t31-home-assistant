"""Constants for the Genial T31 integration."""

from typing import Final

DOMAIN: Final = "genial_t31"
DEFAULT_NAME: Final = "Genial T31 Thermometer"
MANUFACTURER: Final = "Genial"
MODEL: Final = "T31"

SERVICE_UUID: Final = "00001809-0000-1000-8000-00805f9b34fb"
NOTIFY_CHARACTERISTIC_UUID: Final = "0000fff1-0000-1000-8000-00805f9b34fb"
WRITE_CHARACTERISTIC_UUID: Final = "0000fff2-0000-1000-8000-00805f9b34fb"

STALE_AFTER_SECONDS: Final = 45
RETRY_INTERVAL_SECONDS: Final = 60

