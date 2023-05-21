"""Support for collecting data from Hummingbot instances into binary_sensors."""
from __future__ import annotations

from typing import Any

from homeassistant.components import mqtt
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .base import HbotBase
from .const import _LOGGER, TOPIC, TYPES_BINARY_SENSORS
from .hummingbot_coordinator import HbotInstance, HbotManager


def discover_binary_sensors(
    hass: HomeAssistant, hbot_instance: HbotInstance
) -> list[HbotBinarySensor]:
    """Given a topic, dynamically create the right binary_sensor type.

    Async friendly.
    """
    binary_sensors = list()

    for binary_sensor_type in TYPES_BINARY_SENSORS:

        if hbot_instance.get_binary_sensor(binary_sensor_type) is not None:
            continue

        new_binary_sensor = HbotBinarySensor(hass, hbot_instance, binary_sensor_type)

        _LOGGER.debug(f"Adding binary_sensor {new_binary_sensor.name}")

        binary_sensors.append(hbot_instance.add_binary_sensor(new_binary_sensor))

    return binary_sensors


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Hummingbot binary_sensor entry."""
    _LOGGER.debug("Set up binary_sensors start.")

    @callback
    def async_binary_sensor_event_received(msg: mqtt.ReceiveMessage) -> None:
        HbotManager.instance().async_process_entity_mqtt_discovery(hass, msg, discover_binary_sensors, async_add_entities)

    entry.async_on_unload(await mqtt.async_subscribe(hass, TOPIC, async_binary_sensor_event_received, 0))

    _LOGGER.debug("Set up binary_sensors done.")


class HbotBinarySensor(HbotBase, BinarySensorEntity):
    """Representation of an Hummingbot binary_sensor."""

    def __init__(self, *args, **kwargs):
        """Initialize the binary_sensor."""
        super().__init__(*args, **kwargs)

    def _slug(self) -> str:
        return f"binary_sensor.{slugify(self._attr_name)}"

    def set_event(self, event: dict[str, Any]) -> None:
        """Update the binary_sensor with the most recent event."""
        ev = {}
        ev.update(event)

        if (new_state := ev.get(self._state_key, None)) is not None:
            self._attr_is_on = bool(new_state)

        self.update_attributes_with_event(ev)

        self.async_safe_write_ha_state()
