"""Adds config flow for Hummingbot integration."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_STATUS_UPDATE_FREQUENCY,
    CONF_STRATEGY_NAME_HELPER,
    DEFAULT_STATUS_UPDATE_INTERVAL,
    DOMAIN,
)


class HummingbotConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hummingbot integration."""

    VERSION = 1

    entry: ConfigEntry | None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> HummingbotOptionsFlowHandler:
        """Get the options flow for this handler."""
        return HummingbotOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=DOMAIN,
            data={},
        )


class HummingbotOptionsFlowHandler(OptionsFlow):
    """Handle Hummingbot options."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize Hummingbot options flow."""
        self.entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage Hummingbot options."""
        errors = {}

        if user_input:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_STATUS_UPDATE_FREQUENCY,
                        description={
                            "suggested_value": self.entry.options.get(CONF_STATUS_UPDATE_FREQUENCY, DEFAULT_STATUS_UPDATE_INTERVAL)
                        },
                    ): int,
                    vol.Optional(
                        CONF_STRATEGY_NAME_HELPER,
                        description={
                            "suggested_value": self.entry.options.get(CONF_STRATEGY_NAME_HELPER)
                        },
                    ): vol.In(
                        {
                            **{state.entity_id: state.name for state in self.hass.states.async_all("input_text")},
                        }
                    ),
                },
            ),
            errors=errors,
        )
