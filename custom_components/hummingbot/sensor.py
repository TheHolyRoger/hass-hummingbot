"""Support for collecting data from Hummingbot instances into sensors."""
from __future__ import annotations

from typing import Any

from homeassistant.components import mqtt
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .base import HbotBase
from .const import (
    _LOGGER,
    TOPIC,
    TYPE_ENTITY_ACTIVE_ORDERS,
    TYPE_ENTITY_STRATEGY_STATUS,
    TYPES_SENSORS,
)
from .hummingbot_coordinator import HbotInstance, HbotManager


def discover_sensors(
    hass: HomeAssistant, hbot_instance: HbotInstance
) -> list[HbotSensor]:
    """Given a topic, dynamically create the right sensor type.

    Async friendly.
    """
    sensors = list()

    for sensor_type in TYPES_SENSORS:

        if hbot_instance.get_sensor(sensor_type) is not None:
            continue

        units = "orders" if sensor_type == TYPE_ENTITY_ACTIVE_ORDERS else None

        new_sensor = HbotSensor(hass, hbot_instance, sensor_type, unit_of_measurement=units)

        _LOGGER.debug(f"Adding sensor {new_sensor.name}")

        sensors.append(hbot_instance.add_sensor(new_sensor))

    return sensors


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Hummingbot sensors entry."""
    _LOGGER.debug("Set up sensors start.")

    @callback
    def async_sensor_event_received(msg: mqtt.ReceiveMessage) -> None:
        HbotManager.instance().async_process_entity_mqtt_discovery(hass, msg, discover_sensors, async_add_entities)

    entry.async_on_unload(await mqtt.async_subscribe(hass, TOPIC, async_sensor_event_received, 0))

    _LOGGER.debug("Set up sensors done.")


class HbotSensor(HbotBase, SensorEntity):
    """Representation of an Hummingbot sensor."""

    def __init__(self, *args, **kwargs):
        """Initialize the sensor."""
        super().__init__(*args, **kwargs)

        if self._hbot_entity_type == TYPE_ENTITY_STRATEGY_STATUS:
            self._attr_device_class = SensorDeviceClass.ENUM

    def _slug(self) -> str:
        return f"sensor.{slugify(self._attr_name)}"

    def set_event(self, event: dict[str, Any]) -> None:
        """Update the sensor with the most recent event."""
        ev = {}
        ev.update(event)

        self._attr_native_value = ev.get(self._state_key, None)

        self.update_attributes_with_event(ev)

        self.async_safe_write_ha_state()
