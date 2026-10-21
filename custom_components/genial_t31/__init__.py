"""The Genial T31 Thermometer integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import GenialT31Coordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]

type GenialT31ConfigEntry = ConfigEntry[GenialT31Coordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: GenialT31ConfigEntry
) -> bool:
    """Set up a Genial T31 from a config entry."""
    coordinator = GenialT31Coordinator(hass, entry)
    entry.runtime_data = coordinator
    await coordinator.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: GenialT31ConfigEntry
) -> bool:
    """Unload a Genial T31 config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_stop()
    return unload_ok

