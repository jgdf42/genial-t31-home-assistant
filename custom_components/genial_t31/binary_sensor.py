"""Binary sensors for the Genial T31 Thermometer."""

from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GenialT31ConfigEntry
from .entity import GenialT31Entity

if TYPE_CHECKING:
    from .coordinator import GenialT31Coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GenialT31ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the connection-status entity."""
    async_add_entities(
        [T31ConnectionSensor(entry.runtime_data), T31WornSensor(entry.runtime_data)]
    )


class T31ConnectionSensor(GenialT31Entity, BinarySensorEntity):
    """Whether the thermometer is connected and reporting fresh data."""

    entity_description = BinarySensorEntityDescription(
        key="connected",
        translation_key="connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    def __init__(self, coordinator: "GenialT31Coordinator") -> None:
        super().__init__(coordinator, "connected")

    @property
    def is_on(self) -> bool:
        """Return true when the connection has fresh telemetry."""
        return self.coordinator.data.connected


class T31WornSensor(GenialT31Entity, BinarySensorEntity):
    """Whether sustained temperature indicates that the probe is being worn."""

    entity_description = BinarySensorEntityDescription(
        key="worn",
        translation_key="worn",
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    def __init__(self, coordinator: "GenialT31Coordinator") -> None:
        super().__init__(coordinator, "worn")

    @property
    def is_on(self) -> bool | None:
        """Return the confirmed wear state."""
        return self.coordinator.data.worn

