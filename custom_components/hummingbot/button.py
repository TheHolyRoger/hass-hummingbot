"""Support for collecting data from Hummingbot instances."""
from __future__ import annotations

from homeassistant.components import mqtt
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .base import HbotBase
from .const import (
    _LOGGER,
    COMMAND_TOPIC,
    TOPIC,
    TYPE_ENTITY_STRATEGY_GET_STATUS,
    TYPE_ENTITY_STRATEGY_IMPORT,
    TYPE_ENTITY_STRATEGY_START,
    TYPE_ENTITY_STRATEGY_STOP,
    TYPES_BUTTONS,
)
from .hummingbot_coordinator import HbotManager


def discover_buttons(hass, mgr, hbot_instance, endpoint, payload):
    """Given a topic, dynamically create the right button type.

    Async friendly.
    """
    buttons = list()

    for button_type in TYPES_BUTTONS:

        if hbot_instance.get_button(button_type) is not None:
            continue

        new_button = HbotButton(hass, hbot_instance, button_type)
        _LOGGER.debug(f"Adding button {new_button.name}")
        hbot_instance.add_button(new_button)
        buttons.append(new_button)

    return buttons


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Hummingbot buttons entry."""
    _LOGGER.debug("Set up buttons.")

    @callback
    def async_button_event_received(msg: mqtt.ReceiveMessage) -> None:
        mgr = HbotManager.instance()

        hbot_instance, endpoint = mgr.get_hbot_instance_and_endpoint(hass, msg.topic)

        if hbot_instance is None:
            return

        event = mgr.extract_event_payload(hbot_instance, endpoint, msg.payload)

        if event is None:
            return

        buttons = discover_buttons(hass, mgr, hbot_instance, endpoint, event)

        if buttons is None:
            return

        if len(buttons) > 0:
            async_add_entities(buttons, False)

    entry.async_on_unload(await mqtt.async_subscribe(hass, TOPIC, async_button_event_received, 0))


class HbotButton(HbotBase, ButtonEntity):
    """Representation of an Hummingbot button."""

    def __init__(self, hass, hbot_instance, hbot_entity_type, icon=None, device_class=None):
        """Initialize the button."""
        self._hbot_instance = hbot_instance
        self._hbot_entity_type = hbot_entity_type
        self._attr_name = self._build_name()
        self._attr_unique_id = self._build_unique_id()
        self.hass = hass
        self.entity_id = self._slug()
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._attr_device_info = self._build_device_info()
        self._attr_available = False
        self._command_topic = self._build_cmd_topic()
        self._hbot_entity_added = None

    def _build_cmd_topic(self):
        if self._hbot_entity_type == TYPE_ENTITY_STRATEGY_START:
            return COMMAND_TOPIC.format(self._hbot_instance_id, "start")
        elif self._hbot_entity_type == TYPE_ENTITY_STRATEGY_GET_STATUS:
            return COMMAND_TOPIC.format(self._hbot_instance_id, "status")
        elif self._hbot_entity_type == TYPE_ENTITY_STRATEGY_STOP:
            return COMMAND_TOPIC.format(self._hbot_instance_id, "stop")
        elif self._hbot_entity_type == TYPE_ENTITY_STRATEGY_IMPORT:
            return COMMAND_TOPIC.format(self._hbot_instance_id, "import")

    @property
    def _command_payload(self):
        if self._hbot_entity_type == TYPE_ENTITY_STRATEGY_IMPORT:
            strategy_name_state = self.hass.states.get(self._hbot_instance.strategy_helper)
            strategy_name = strategy_name_state.state if strategy_name_state is not None else ""
            data_dict = {"strategy": strategy_name}
            self._hbot_instance.set_last_imported_strategy(strategy_name)
            return self._hbot_instance.get_cmd_payload("hass_replies_import", data_dict)
        else:
            return self._hbot_instance.get_cmd_payload()

    def _slug(self):
        return f"button.{slugify(self._attr_name)}"

    async def async_press(self) -> None:
        await mqtt.async_publish(
            self.hass, self._command_topic, self._command_payload, 0
        )
