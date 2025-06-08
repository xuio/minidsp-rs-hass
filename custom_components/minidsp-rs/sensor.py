from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MiniDSPCoordinator

_LOGGER = logging.getLogger(__name__)


class _LevelSensorBase(CoordinatorEntity[MiniDSPCoordinator], SensorEntity):
    _attr_native_unit_of_measurement = "dBFS"
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self, coordinator: MiniDSPCoordinator, name: str, index: int, key: str
    ):
        super().__init__(coordinator)
        self._key = key  # "input_levels" or "output_levels"
        self._index = index
        self._attr_unique_id = f"{coordinator.address}_{key}_{index}"
        self._attr_name = name

    @property
    def native_value(self):  # type: ignore[override]
        levels: list[Any] | None = (self.coordinator.data or {}).get(self._key)
        if levels and len(levels) > self._index:
            try:
                return int(round(float(levels[self._index])))
            except (TypeError, ValueError):
                return None
        return None

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
        _LOGGER.error("Coordinator not found during sensor platform setup")
        return

    # Determine how many channels we have based on initial data
    data = coordinator.data or {}

    entities: list[SensorEntity] = []

    for key in ("input_levels", "output_levels"):
        levels = data.get(key, [])
        for idx, _ in enumerate(levels):
            friendly = "Input" if key == "input_levels" else "Output"
            name = f"{friendly} Level {idx}"
            entities.append(_LevelSensorBase(coordinator, name, idx, key))

    async_add_entities(entities)
