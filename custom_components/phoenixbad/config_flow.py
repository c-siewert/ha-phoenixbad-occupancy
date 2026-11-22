"""Config and options flow for Phoenixbad."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .api import PhoenixbadClient, PhoenixbadConnectionError, PhoenixbadParseError
from .const import AREAS, DOMAIN


class PhoenixbadConfigFlow(ConfigFlow, domain=DOMAIN):
    """Single-step setup: just check that the website answers."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            client = PhoenixbadClient(async_get_clientsession(self.hass))
            area = AREAS["hallenbad"]
            try:
                await client.async_get_area(area.api_area, area.default_capacity)
            except PhoenixbadConnectionError:
                errors["base"] = "cannot_connect"
            except PhoenixbadParseError:
                errors["base"] = "invalid_response"
            else:
                return self.async_create_entry(title="Phoenixbad", data={})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> PhoenixbadOptionsFlow:
        return PhoenixbadOptionsFlow()


class PhoenixbadOptionsFlow(OptionsFlowWithReload):
    """The "quiet" thresholds; entry reloads on save."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data={k: int(v) for k, v in user_input.items()})

        schema = {
            vol.Required(area.conf_threshold, default=area.default_threshold): NumberSelector(
                NumberSelectorConfig(
                    min=0, max=area.default_capacity, step=1, mode=NumberSelectorMode.BOX
                )
            )
            for area in AREAS.values()
        }
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(schema), self.config_entry.options
            ),
        )
