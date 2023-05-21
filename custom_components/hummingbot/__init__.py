"""The hummingbot component."""
from __future__ import annotations

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import _LOGGER, DOMAIN, PLATFORMS, TOPIC
from .hummingbot_coordinator import HbotManager
from .services import async_register_services


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hummingbot from a config entry."""
    _LOGGER.debug(f"Set up {DOMAIN}.")

    HbotManager.instance().update_with_config_entry()

    async_register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(update_listener))

    @callback
    def async_event_received(msg: mqtt.ReceiveMessage) -> None:
        HbotManager.instance().async_process_mqtt_data_update(hass, msg)

    entry.async_on_unload(await mqtt.async_subscribe(hass, TOPIC, async_event_received, 0))

    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    # await hass.config_entries.async_reload(entry.entry_id)
    HbotManager.instance().update_with_config_entry()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        HbotManager.unload()
        return True
    return False
