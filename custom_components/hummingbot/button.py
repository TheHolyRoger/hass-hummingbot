"""Support for controlling Hummingbot instances with buttons."""
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
from .hummingbot_coordinator import HbotInstance, HbotManager


def discover_buttons(
    hass: HomeAssistant, hbot_instance: HbotInstance
) -> list[HbotButton]:
    """Given a topic, dynamically create the right button type.

    Async friendly.
    """
    buttons = list()

    for button_type in TYPES_BUTTONS:

        if hbot_instance.get_button(button_type) is not None:
            continue

        new_button = HbotButton(hass, hbot_instance, button_type)

        _LOGGER.debug(f"Adding button {new_button.name}")

        buttons.append(hbot_instance.add_button(new_button))

    return buttons


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Hummingbot buttons entry."""
    _LOGGER.debug("Set up buttons start.")

    @callback
    def async_button_event_received(msg: mqtt.ReceiveMessage) -> None:
        HbotManager.instance().async_process_entity_mqtt_discovery(hass, msg, discover_buttons, async_add_entities)

    entry.async_on_unload(await mqtt.async_subscribe(hass, TOPIC, async_button_event_received, 0))

    _LOGGER.debug("Set up buttons done.")


class HbotButton(HbotBase, ButtonEntity):
    """Representation of an Hummingbot button."""

    def __init__(self, *args, **kwargs):
        """Initialize the button."""
        super().__init__(*args, **kwargs)

        self._command_topic = self._build_cmd_topic()

    def _build_cmd_topic(self) -> str:
        if self._hbot_entity_type == TYPE_ENTITY_STRATEGY_START:
            return COMMAND_TOPIC.format(self._hbot_instance_id, "start")
        elif self._hbot_entity_type == TYPE_ENTITY_STRATEGY_GET_STATUS:
            return COMMAND_TOPIC.format(self._hbot_instance_id, "status")
        elif self._hbot_entity_type == TYPE_ENTITY_STRATEGY_STOP:
            return COMMAND_TOPIC.format(self._hbot_instance_id, "stop")
        elif self._hbot_entity_type == TYPE_ENTITY_STRATEGY_IMPORT:
            return COMMAND_TOPIC.format(self._hbot_instance_id, "import")

    @property
    def _command_payload(self) -> str:
        if self._hbot_entity_type == TYPE_ENTITY_STRATEGY_IMPORT:
            strategy_name_state = self.hass.states.get(self._hbot_instance.strategy_helper)
            strategy_name = strategy_name_state.state if strategy_name_state is not None else ""
            data_dict = {"strategy": strategy_name}
            self._hbot_instance.set_last_imported_strategy(strategy_name)
            return self._hbot_instance.get_cmd_payload("hass_replies_import", data_dict)
        else:
            return self._hbot_instance.get_cmd_payload()

    def _slug(self) -> str:
        return f"button.{slugify(self._attr_name)}"

    async def async_press(self) -> None:
        await mqtt.async_publish(
            self.hass, self._command_topic, self._command_payload, 0
        )
