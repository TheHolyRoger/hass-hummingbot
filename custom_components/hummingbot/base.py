"""Support for collecting data from Hummingbot instances."""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from homeassistant.helpers import entity

from .const import _LOGGER, DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .hummingbot_coordinator import HbotInstance


class HbotBase(entity.Entity):
    """Base representation of a Hummingbot entity."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        hbot_instance: HbotInstance,
        hbot_entity_type: str,
        icon: str = None,
        device_class: str = None,
        unit_of_measurement: str = None,
    ):
        """Initialize the hummingbot entity."""
        self._hbot_instance = hbot_instance
        self._hbot_entity_type = hbot_entity_type
        self._attr_name = self._build_name()
        self._attr_unique_id = self._build_unique_id()
        self.hass = hass
        self.entity_id = self._slug()
        self._state_key = "_state"
        self._attr_icon = icon
        self._attr_device_class = device_class
        self._attr_device_info = self._build_device_info()
        self._attr_available = False
        if unit_of_measurement:
            self._attr_native_unit_of_measurement = unit_of_measurement
        self._hbot_entity_added = None

    @property
    def _hbot_instance_id(self) -> str:
        return self._hbot_instance.instance_id

    @property
    def unique_id(self) -> str:
        return self._attr_unique_id

    @property
    def device_id(self) -> str:
        return "hb_" + self._hbot_instance_id

    @property
    def device_info(self) -> entity.DeviceInfo:
        """Return the device info."""
        return self._attr_device_info

    def _build_unique_id(self) -> str:
        return f"{self._hbot_instance_id}_{self._hbot_entity_type}".replace(" ", "_").lower()

    def _build_name(self) -> str:
        return f"Hummingbot {self._hbot_instance_id} {self._hbot_entity_type}"

    def _build_device_info(self) -> entity.DeviceInfo:
        return entity.DeviceInfo(
            identifiers={(DOMAIN, self._hbot_instance_id)},
            manufacturer="Hummingbot",
            model="Hummingbot",
            name=f"Hummingbot {self._hbot_instance_id}",
        )

    def __repr__(self) -> str:
        return f"{self.unique_id} {self._attr_unique_id} {self._attr_name}"

    def set_available(self) -> None:
        if not self.check_ready():
            return

        if self._attr_available:
            return

        self._attr_available = True
        self.async_write_ha_state()

    def set_unavailable(self) -> None:
        if not self.check_ready():
            return

        if not self._attr_available:
            return

        self._attr_available = False
        self.async_write_ha_state()

    def check_added_time(self) -> bool:
        if self._hbot_entity_added is None:
            self.set_added_time()
            return False

        time_now = int(time.time())

        if time_now - 3 > self._hbot_entity_added:
            return True

        return False

    def set_added_time(self) -> None:
        self._hbot_entity_added = int(time.time())

    def check_ready(self) -> bool:
        if self.entity_id not in self._hbot_instance.ent_registry.entities:
            return False

        return self.check_added_time()

    def update_attributes_with_event(self, event) -> None:
        if self._state_key in event:
            del event[self._state_key]

        self._attr_extra_state_attributes = event

    def async_safe_write_ha_state(self) -> None:
        if self.hass is not None:
            self.async_write_ha_state()
        else:
            _LOGGER.warning(f"Unable to update state for {self}, entity has been aborted.")
