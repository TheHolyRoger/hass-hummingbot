"""Support for collecting data from Hummingbot instances."""
from __future__ import annotations

from homeassistant.components import mqtt
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .base import HbotBase
from .const import _LOGGER, TOPIC, TYPES_BINARY_SENSORS
from .hummingbot_coordinator import HbotManager


def discover_binary_sensors(hass, mgr, hbot_instance, endpoint, payload):
    """Given a topic, dynamically create the right binary_sensor type.

    Async friendly.
    """
    binary_sensors = list()

    for binary_sensor_type in TYPES_BINARY_SENSORS:

        if hbot_instance.get_binary_sensor(binary_sensor_type) is not None:
            continue

        new_binary_sensor = HbotBinarySensor(hass, hbot_instance, binary_sensor_type)
        _LOGGER.debug(f"Adding binary_sensor {new_binary_sensor.name}")
        hbot_instance.add_binary_sensor(new_binary_sensor)
        binary_sensors.append(new_binary_sensor)

    return binary_sensors


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Hummingbot binary_sensor entry."""
    _LOGGER.debug("Set up binary_sensors.")

    @callback
    def async_binary_sensor_event_received(msg: mqtt.ReceiveMessage) -> None:
        _LOGGER.debug("Binary event received.")
        mgr = HbotManager.instance()

        hbot_instance, endpoint = mgr.get_hbot_instance_and_endpoint(hass, msg.topic)
        _LOGGER.debug(hbot_instance)

        if hbot_instance is None:
            return

        event = mgr.extract_event_payload(hbot_instance, endpoint, msg.payload)
        _LOGGER.debug(event)

        if event is None:
            return

        binary_sensors = discover_binary_sensors(hass, mgr, hbot_instance, endpoint, event)

        if binary_sensors is None:
            return

        if len(binary_sensors) > 0:
            async_add_entities(binary_sensors, False)

    entry.async_on_unload(await mqtt.async_subscribe(hass, TOPIC, async_binary_sensor_event_received, 0))


class HbotBinarySensor(HbotBase, BinarySensorEntity):
    """Representation of an Hummingbot binary_sensor."""

    def __init__(self, hass, hbot_instance, hbot_entity_type, icon=None, device_class=None):
        """Initialize the binary_sensor."""
        self._hbot_instance = hbot_instance
        self._hbot_entity_type = hbot_entity_type
        self._attr_name = self._build_name()
        self._attr_unique_id = self._build_unique_id()
        self.hass = hass
        self.entity_id = self._slug()
        self._state = None
        self._state_key = "_state"
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._attr_device_info = self._build_device_info()
        self._attr_available = False
        self._hbot_entity_added = None

    def _slug(self):
        return f"binary_sensor.{slugify(self._attr_name)}"

    @property
    def is_on(self):
        """Return true if the binary_sensor is on."""
        return bool(self._state)

    def set_event(self, event):
        """Update the binary_sensor with the most recent event."""
        ev = {}
        ev.update(event)
        self._state = ev.get(self._state_key, None)
        if self._state_key in ev:
            del ev[self._state_key]

        self._attr_extra_state_attributes = ev
        self.async_write_ha_state()
