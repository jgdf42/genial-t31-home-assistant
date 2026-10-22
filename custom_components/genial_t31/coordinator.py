"""Bluetooth connection coordinator for the Genial T31."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
import logging

from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from homeassistant.components.bluetooth import (
    BluetoothChange,
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_ble_device_from_address,
    async_register_callback,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    DEFAULT_NAME,
    NOTIFY_CHARACTERISTIC_UUID,
    POWER_SAVE_RECHECK_SECONDS,
    POWER_SAVE_SECONDS,
    RETRY_INTERVAL_SECONDS,
    STALE_AFTER_SECONDS,
    UNWORN_CONFIRM_SECONDS,
    UNWORN_TEMPERATURE_CELSIUS,
    WRITE_CHARACTERISTIC_UUID,
)
from .protocol import (
    COMMAND_BATTERY,
    COMMAND_CONNECT_RESPONSE,
    COMMAND_SETTINGS,
    COMMAND_SYNC_REQUEST,
    COMMAND_TEMPERATURE,
    ProtocolError,
    battery_command,
    connect_command,
    decode_battery,
    decode_temperature,
    extract_frames,
    settings_command,
    sync_time_command,
)
from .trend import TemperatureTrend
from .wear import WearMonitor

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class T31Data:
    """State published to Home Assistant entities."""

    connected: bool = False
    worn: bool | None = None
    temperature_celsius: float | None = None
    auxiliary_temperature_celsius: float | None = None
    temperature_baseline_celsius: float | None = None
    temperature_rise_celsius: float | None = None
    temperature_rate_celsius_per_minute: float | None = None
    battery_percent: int | None = None
    battery_level: int | None = None
    voltage_mv: int | None = None
    rssi: int | None = None
    last_temperature_at: datetime | None = None
    last_seen: datetime | None = None
    protocol_error: str | None = None


class GenialT31Coordinator(DataUpdateCoordinator[T31Data]):
    """Maintain the BLE connection and decode pushed telemetry."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DEFAULT_NAME} {entry.unique_id}",
            update_interval=None,
        )
        self.config_entry = entry
        self.address = entry.unique_id or entry.data[CONF_ADDRESS]
        self._client: BleakClientWithServiceCache | None = None
        self._buffer = bytearray()
        self._trend = TemperatureTrend()
        self._wear = WearMonitor(
            UNWORN_TEMPERATURE_CELSIUS,
            UNWORN_CONFIRM_SECONDS,
            POWER_SAVE_RECHECK_SECONDS,
        )
        self._connect_lock = asyncio.Lock()
        self._write_lock = asyncio.Lock()
        self._notification_lock = asyncio.Lock()
        self._reconnect_task: asyncio.Task[None] | None = None
        self._maintenance_task: asyncio.Task[None] | None = None
        self._unregister_bluetooth: Callable[[], None] | None = None
        self._connected_at: datetime | None = None
        self._connection_last_temperature_at: datetime | None = None
        self._power_save_until: datetime | None = None
        self._stopping = False
        self.async_set_updated_data(T31Data())

    async def async_start(self) -> None:
        """Start Bluetooth tracking and connection maintenance."""
        self._stopping = False
        self._unregister_bluetooth = async_register_callback(
            self.hass,
            self._async_bluetooth_callback,
            {"address": self.address},
            BluetoothScanningMode.ACTIVE,
        )
        self._maintenance_task = self.config_entry.async_create_background_task(
            self.hass,
            self._async_maintenance_loop(),
            f"{DEFAULT_NAME} maintenance",
        )
        self._schedule_reconnect()

    async def async_stop(self) -> None:
        """Stop background work and disconnect cleanly."""
        self._stopping = True
        if self._unregister_bluetooth:
            self._unregister_bluetooth()
            self._unregister_bluetooth = None
        for task in (self._reconnect_task, self._maintenance_task):
            if task:
                task.cancel()
        self._reconnect_task = None
        self._maintenance_task = None
        await self._async_disconnect()

    @callback
    def _async_bluetooth_callback(
        self, service_info: BluetoothServiceInfoBleak, _change: BluetoothChange
    ) -> None:
        """Record signal strength and connect when the thermometer is seen."""
        self.async_set_updated_data(
            replace(
                self.data,
                rssi=service_info.rssi,
                last_seen=datetime.now(UTC),
            )
        )
        self._schedule_reconnect()

    @callback
    def _schedule_reconnect(self) -> None:
        now = datetime.now(UTC)
        if self._power_save_until is not None:
            if now < self._power_save_until:
                return
            self._power_save_until = None
        if self._stopping or (self._client and self._client.is_connected):
            return
        if self._reconnect_task and not self._reconnect_task.done():
            return
        self._reconnect_task = self.config_entry.async_create_background_task(
            self.hass,
            self._async_connect(),
            f"{DEFAULT_NAME} connection",
        )

    async def _async_maintenance_loop(self) -> None:
        """Detect stale streams and retry unavailable connections."""
        while True:
            await asyncio.sleep(15)
            client = self._client
            activity_at = self._connection_last_temperature_at or self._connected_at
            if client and client.is_connected and activity_at is not None:
                age = (datetime.now(UTC) - activity_at).total_seconds()
                if age > STALE_AFTER_SECONDS:
                    _LOGGER.debug("Temperature stream stale for %.1f seconds", age)
                    await self._async_disconnect()
            if not self._client or not self._client.is_connected:
                self._schedule_reconnect()
                await asyncio.sleep(RETRY_INTERVAL_SECONDS - 15)

    async def _async_connect(self) -> None:
        async with self._connect_lock:
            if self._stopping or (self._client and self._client.is_connected):
                return
            device = async_ble_device_from_address(
                self.hass, self.address, connectable=True
            )
            if device is None:
                return
            client: BleakClientWithServiceCache | None = None
            try:
                client = await establish_connection(
                    BleakClientWithServiceCache,
                    device,
                    DEFAULT_NAME,
                    self._on_disconnect,
                    use_services_cache=True,
                )
                self._client = client
                self._connected_at = datetime.now(UTC)
                self._connection_last_temperature_at = None
                self._wear.begin_connection()
                self._buffer.clear()
                await client.start_notify(
                    NOTIFY_CHARACTERISTIC_UUID, self._notification_handler
                )
                await self._write(connect_command())
            except (BleakError, TimeoutError) as err:
                _LOGGER.debug("Unable to connect to Genial T31 %s: %s", self.address, err)
                self._client = None
                self._connected_at = None
                self._connection_last_temperature_at = None
                if client and client.is_connected:
                    try:
                        await client.disconnect()
                    except BleakError:
                        pass
                self.async_set_updated_data(replace(self.data, connected=False))

    async def _async_disconnect(self) -> None:
        client = self._client
        self._client = None
        self._connected_at = None
        self._connection_last_temperature_at = None
        if client and client.is_connected:
            try:
                await client.disconnect()
            except BleakError:
                pass
        self.async_set_updated_data(replace(self.data, connected=False))

    @callback
    def _on_disconnect(self, client: BleakClientWithServiceCache) -> None:
        if client is self._client:
            self._client = None
            self._connected_at = None
            self._connection_last_temperature_at = None
        self.async_set_updated_data(replace(self.data, connected=False))
        self._schedule_reconnect()

    async def _write(self, payload: bytes) -> None:
        client = self._client
        if not client or not client.is_connected:
            raise BleakError("Genial T31 is not connected")
        async with self._write_lock:
            await client.write_gatt_char(
                WRITE_CHARACTERISTIC_UUID, payload, response=False
            )

    def _notification_handler(self, _: object, data: bytearray) -> None:
        """Schedule ordered handling of a BLE notification."""
        self.hass.async_create_task(
            self._async_process_notification(bytes(data)),
            f"{DEFAULT_NAME} notification",
        )

    async def _async_process_notification(self, data: bytes) -> None:
        async with self._notification_lock:
            self._buffer.extend(data)
            for frame in extract_frames(self._buffer):
                try:
                    await self._async_handle_frame(frame.command, frame.body)
                except ProtocolError as err:
                    _LOGGER.debug("Invalid Genial T31 notification: %s", err)
                    self.async_set_updated_data(
                        replace(self.data, protocol_error=str(err))
                    )

    async def _async_handle_frame(self, command: int, body: bytes) -> None:
        now = datetime.now(UTC)
        if command == COMMAND_CONNECT_RESPONSE:
            if len(body) < 2:
                raise ProtocolError("Connect response is too short")
            self.async_set_updated_data(
                replace(
                    self.data,
                    battery_percent=body[1] if body[1] <= 100 else None,
                    last_seen=now,
                    protocol_error=None,
                )
            )
            return
        if command == COMMAND_SETTINGS:
            await self._write(settings_command())
            return
        if command == COMMAND_SYNC_REQUEST:
            await self._write(sync_time_command())
            await asyncio.sleep(0.5)
            await self._write(battery_command())
            return
        if command == COMMAND_TEMPERATURE:
            reading = decode_temperature(body)
            self._connection_last_temperature_at = now
            baseline, rise, rate = self._trend.update(
                now, reading.temperature_celsius
            )
            worn, should_disconnect = self._wear.update(
                now, reading.temperature_celsius
            )
            self.async_set_updated_data(
                replace(
                    self.data,
                    connected=True,
                    worn=worn,
                    temperature_celsius=reading.temperature_celsius,
                    auxiliary_temperature_celsius=(
                        reading.auxiliary_temperature_celsius
                    ),
                    temperature_baseline_celsius=baseline,
                    temperature_rise_celsius=rise,
                    temperature_rate_celsius_per_minute=rate,
                    last_temperature_at=now,
                    last_seen=now,
                    protocol_error=None,
                )
            )
            if should_disconnect:
                self._power_save_until = now + timedelta(seconds=POWER_SAVE_SECONDS)
                _LOGGER.debug(
                    "Thermometer confirmed unworn; suppressing reconnects for %s seconds",
                    POWER_SAVE_SECONDS,
                )
                await self._async_disconnect()
            return
        if command == COMMAND_BATTERY:
            battery = decode_battery(body)
            self.async_set_updated_data(
                replace(
                    self.data,
                    battery_level=battery.level,
                    battery_percent=battery.percent,
                    voltage_mv=battery.voltage_mv,
                    last_seen=now,
                    protocol_error=None,
                )
            )


