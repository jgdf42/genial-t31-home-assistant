"""Sensors for the Genial T31 Thermometer."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfElectricPotential,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GenialT31ConfigEntry
from .coordinator import T31Data
from .entity import GenialT31Entity

if TYPE_CHECKING:
    from .coordinator import GenialT31Coordinator


@dataclass(frozen=True, kw_only=True)
class T31SensorDescription(SensorEntityDescription):
    """Describe a Genial sensor."""

    value_fn: Callable[[T31Data], float | int | datetime | None]


SENSORS = (
    T31SensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.temperature_celsius,
    ),
    T31SensorDescription(
        key="auxiliary_temperature",
        translation_key="auxiliary_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.auxiliary_temperature_celsius,
    ),
    T31SensorDescription(
        key="temperature_baseline",
        translation_key="temperature_baseline",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.temperature_baseline_celsius,
    ),
    T31SensorDescription(
        key="temperature_rise",
        translation_key="temperature_rise",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.temperature_rise_celsius,
    ),
    T31SensorDescription(
        key="temperature_rate",
        translation_key="temperature_rate",
        native_unit_of_measurement="°C/min",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.temperature_rate_celsius_per_minute,
    ),
    T31SensorDescription(
        key="battery",
        translation_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.battery_percent,
    ),
    T31SensorDescription(
        key="battery_voltage",
        translation_key="battery_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.MILLIVOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.voltage_mv,
    ),
    T31SensorDescription(
        key="rssi",
        translation_key="rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: data.rssi,
    ),
    T31SensorDescription(
        key="last_reading",
        translation_key="last_reading",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data.last_temperature_at,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GenialT31ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Genial T31 sensors."""
    async_add_entities(
        T31Sensor(entry.runtime_data, description) for description in SENSORS
    )


class T31Sensor(GenialT31Entity, SensorEntity):
    """A Genial T31 sensor."""

    entity_description: T31SensorDescription

    def __init__(
        self,
        coordinator: "GenialT31Coordinator",
        description: T31SensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | datetime | None:
        """Return the current value."""
        return self.entity_description.value_fn(self.coordinator.data)

