"""Support for collecting data from Hummingbot instances."""
from __future__ import annotations

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
from .hummingbot_coordinator import HbotManager


def discover_sensors(hass, mgr, hbot_instance, endpoint, payload):
    """Given a topic, dynamically create the right sensor type.

    Async friendly.
    """
    sensors = list()

    for sensor_type in TYPES_SENSORS:

        if hbot_instance.get_sensor(sensor_type) is not None:
            continue

        units = "orders" if sensor_type == TYPE_ENTITY_ACTIVE_ORDERS else None
        new_sensor = HbotSensor(hass, hbot_instance, sensor_type, units=units)
        _LOGGER.debug(f"Adding sensor {new_sensor.name}")
        hbot_instance.add_sensor(new_sensor)
        sensors.append(new_sensor)

    return sensors


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Hummingbot sensors entry."""
    _LOGGER.debug("Set up sensors.")

    @callback
    def async_sensor_event_received(msg: mqtt.ReceiveMessage) -> None:
        mgr = HbotManager.instance()

        hbot_instance, endpoint = mgr.get_hbot_instance_and_endpoint(hass, msg.topic)

        if hbot_instance is None:
            return

        event = mgr.extract_event_payload(hbot_instance, endpoint, msg.payload)

        if event is None:
            return

        sensors = discover_sensors(hass, mgr, hbot_instance, endpoint, event)

        if sensors is None:
            return

        if len(sensors) > 0:
            async_add_entities(sensors, False)

    entry.async_on_unload(await mqtt.async_subscribe(hass, TOPIC, async_sensor_event_received, 0))


class HbotSensor(HbotBase, SensorEntity):
    """Representation of an Hummingbot sensor."""

    def __init__(self, hass, hbot_instance, hbot_entity_type, units=None, icon=None, device_class=None):
        """Initialize the sensor."""
        self._hbot_instance = hbot_instance
        self._hbot_entity_type = hbot_entity_type
        self._attr_name = self._build_name()
        self._attr_unique_id = self._build_unique_id()
        self.hass = hass
        self.entity_id = self._slug()
        self._state_key = "_state"
        self._attr_native_unit_of_measurement = units
        self._attr_icon = icon
        self._attr_device_class = SensorDeviceClass.ENUM if hbot_entity_type == TYPE_ENTITY_STRATEGY_STATUS else device_class
        self._attr_device_info = self._build_device_info()
        self._attr_available = False
        self._hbot_entity_added = None

    def _slug(self):
        return f"sensor.{slugify(self._attr_name)}"

    def set_event(self, event):
        # _LOGGER.warning(f"Updating state for {self}.")
        """Update the sensor with the most recent event."""
        ev = {}
        ev.update(event)
        self._attr_native_value = ev.get(self._state_key, None)
        if self._state_key in ev:
            del ev[self._state_key]

        self._attr_extra_state_attributes = ev
        if self.hass is not None:
            self.async_write_ha_state()
        else:
            _LOGGER.warning(f"Unable to update state for {self}, hass aborted.")
