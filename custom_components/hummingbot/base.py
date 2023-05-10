"""Support for collecting data from Hummingbot instances."""
from __future__ import annotations

import time

from homeassistant.helpers import entity

from .const import DOMAIN


class HbotBase(entity.Entity):
    """Base representation of a Hummingbot entity."""

    _attr_should_poll = False

    @property
    def _hbot_instance_id(self):
        return self._hbot_instance.instance_id

    def _build_unique_id(self):
        return f"{self._hbot_instance_id}_{self._hbot_entity_type}".replace(" ", "_").lower()

    def _build_name(self):
        return f"Hummingbot {self._hbot_instance_id} {self._hbot_entity_type}"

    def _build_device_info(self):
        return entity.DeviceInfo(
            identifiers={(DOMAIN, self._hbot_instance_id)},
            manufacturer="Hummingbot",
            model="Hummingbot",
            name=f"Hummingbot {self._hbot_instance_id}",
        )

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

    def __repr__(self):
        return f"{self.unique_id} {self._attr_unique_id} {self._attr_name}"

    def set_available(self):
        if not self.check_ready():
            return

        if self._attr_available:
            return

        self._attr_available = True
        self.async_write_ha_state()

    def set_unavailable(self):
        if not self.check_ready():
            return

        if not self._attr_available:
            return

        self._attr_available = False
        self.async_write_ha_state()

    def check_added_time(self):
        if self._hbot_entity_added is None:
            self.set_added_time()
            return False

        time_now = int(time.time())

        if time_now - 3 > self._hbot_entity_added:
            return True

        return False

    def set_added_time(self):
        self._hbot_entity_added = int(time.time())

    def check_ready(self):
        if self.entity_id not in self._hbot_instance.ent_registry.entities:
            return False

        return self.check_added_time()
