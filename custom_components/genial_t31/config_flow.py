"""Config flow for the Genial T31 Thermometer."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import DEFAULT_NAME, DOMAIN, SERVICE_UUID


class GenialT31ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle Genial T31 configuration."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery: BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle Bluetooth discovery."""
        await self.async_set_unique_id(discovery_info.address, raise_on_progress=False)
        self._abort_if_unique_id_configured()
        self._discovery = discovery_info
        self.context["title_placeholders"] = {
            "name": discovery_info.name or DEFAULT_NAME
        }
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered thermometer."""
        assert self._discovery is not None
        if user_input is not None:
            return self.async_create_entry(
                title=DEFAULT_NAME,
                data={CONF_ADDRESS: self._discovery.address},
            )
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={
                "name": self._discovery.name or DEFAULT_NAME,
                "address": self._discovery.address,
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select a currently discovered Genial thermometer."""
        discoveries = self._discoveries()
        errors: dict[str, str] = {}
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            if address not in discoveries:
                errors["base"] = "cannot_connect"
            else:
                self._discovery = discoveries[address]
                await self.async_set_unique_id(address, raise_on_progress=False)
                self._abort_if_unique_id_configured()
                return await self.async_step_confirm()

        options = [
            {
                "value": address,
                "label": f"{info.name or DEFAULT_NAME} ({address})",
            }
            for address, info in discoveries.items()
        ]
        if not options:
            return self.async_abort(reason="no_devices_found")
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ADDRESS): SelectSelector(
                        SelectSelectorConfig(
                            options=options,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            errors=errors,
        )

    def _discoveries(self) -> dict[str, BluetoothServiceInfoBleak]:
        configured = {
            entry.unique_id for entry in self._async_current_entries() if entry.unique_id
        }
        return {
            info.address: info
            for info in async_discovered_service_info(self.hass, connectable=True)
            if (info.name or "").startswith("Genial-T31")
            and SERVICE_UUID in {uuid.lower() for uuid in info.service_uuids}
            and info.address not in configured
        }

