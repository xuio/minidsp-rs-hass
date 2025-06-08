from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MiniDSPCoordinator

_LOGGER = logging.getLogger(__name__)


class DiracLiveSwitch(CoordinatorEntity[MiniDSPCoordinator], SwitchEntity):
    """Switch to enable/disable Dirac Live."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:autorenew"

    def __init__(self, coordinator: MiniDSPCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_dirac"
        self._attr_name = "Dirac Live"

    # ---------------------------------------------------------------------
    @property
    def is_on(self):  # type: ignore[override]
        return (self.coordinator.data or {}).get("master", {}).get("dirac")

    async def async_turn_on(self):  # type: ignore[override]
        await self.coordinator._api.async_set_dirac(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self):  # type: ignore[override]
        await self.coordinator._api.async_set_dirac(False)
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self):  # type: ignore[override]
        return {
            "identifiers": {(DOMAIN, self.coordinator.address)},
            "name": self.coordinator.name,
        }


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    stored = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator: MiniDSPCoordinator | None = stored.get("coordinator")
    if coordinator is None:
        _LOGGER.error("Coordinator not found during switch platform setup")
        return

    async_add_entities([DiracLiveSwitch(coordinator)])
