"""Support for hummingbot services."""
from __future__ import annotations

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall, callback

from .const import ATTR_INSTANCE_ID, ATTR_STRATEGY_NAME, DOMAIN
from .hummingbot_coordinator import HbotManager

IMPORT_STRATEGY = "import_strategy"

SERVICE_IMPORT_STRATEGY_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_INSTANCE_ID): cv.string,
        vol.Optional(ATTR_STRATEGY_NAME): cv.string,
    }
)


@callback
def _async_register_import_strategy_service(hass: HomeAssistant) -> None:
    async def async_handle_import_strategy_service(service: ServiceCall) -> None:
        """Handle calls to the import_strategy service."""
        kwargs = service.data
        instance_id = kwargs.get(ATTR_INSTANCE_ID)
        strategy_name = kwargs.get(ATTR_STRATEGY_NAME)
        HbotManager.instance().send_import_command(hass, instance_id, strategy_name)

    hass.services.async_register(
        DOMAIN,
        IMPORT_STRATEGY,
        async_handle_import_strategy_service,
        schema=SERVICE_IMPORT_STRATEGY_SCHEMA,
    )


@callback
def async_register_services(hass: HomeAssistant) -> None:
    """Register hummingbot services."""
    if not hass.services.has_service(DOMAIN, IMPORT_STRATEGY):
        _async_register_import_strategy_service(hass)
