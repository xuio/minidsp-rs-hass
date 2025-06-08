from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SOURCES
from .coordinator import MiniDSPCoordinator

_LOGGER = logging.getLogger(__name__)

# Map friendly labels (as shown to user) to API values
_SOURCE_MAP = {
    "Analog": "Analog",
    "TOSLINK": "Toslink",
    "SPDIF": "Spdif",
    "USB": "Usb",
    "Bluetooth": "Bluetooth",
}

# Preset map copied from select.py
_PRESET_MAP = {
    "Preset 1": 0,
    "Preset 2": 1,
    "Preset 3": 2,
    "Preset 4": 3,
}

_MIN_DB = -127.0
_MAX_DB = 0.0


class MiniDSPMediaPlayer(CoordinatorEntity[MiniDSPCoordinator], MediaPlayerEntity):
    """MediaPlayer entity that encapsulates MiniDSP controls."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:amplifier"

    _attr_supported_features = (
        MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.SELECT_SOURCE
        | MediaPlayerEntityFeature.SELECT_SOUND_MODE
    )

    def __init__(self, coordinator: MiniDSPCoordinator):
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_mediaplayer"
        self._attr_name = coordinator.name or "MiniDSP"

    # ------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------

    @property
    def state(self):  # type: ignore[override]
        # MiniDSP has no explicit power state; always ON if reachable.
        return STATE_ON if self.coordinator.last_update_success else STATE_OFF

    # Volume conversion helpers
    def _db_to_level(self, gain: float | None) -> float | None:
        if gain is None:
            return None
        # Map [_MIN_DB, _MAX_DB] to [0.0, 1.0]
        return max(0.0, min(1.0, (gain - _MIN_DB) / (_MAX_DB - _MIN_DB)))

    def _level_to_db(self, level: float) -> float:
        return (_MAX_DB - _MIN_DB) * level + _MIN_DB

    @property
    def volume_level(self):  # type: ignore[override]
        gain = (self.coordinator.data or {}).get("master", {}).get("volume")
        return self._db_to_level(gain)

    @property
    def is_volume_muted(self):  # type: ignore[override]
        return (self.coordinator.data or {}).get("master", {}).get("mute")

    @property
    def source(self):  # type: ignore[override]
        raw = (self.coordinator.data or {}).get("master", {}).get("source")
        for label, raw_val in _SOURCE_MAP.items():
            if raw_val == raw:
                return label
        return raw

    @property
    def source_list(self):  # type: ignore[override]
        return list(_SOURCE_MAP.keys())

    @property
    def sound_mode(self):  # type: ignore[override]
        idx = (self.coordinator.data or {}).get("master", {}).get("preset")
        for label, val in _PRESET_MAP.items():
            if val == idx:
                return label
        return None

    @property
    def sound_mode_list(self):  # type: ignore[override]
        return list(_PRESET_MAP.keys())

    @property
    def extra_state_attributes(self):
        return {
            "dirac": (self.coordinator.data or {}).get("master", {}).get("dirac"),
        }

    # ------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------

    async def async_set_volume_level(self, volume: float):  # type: ignore[override]
        db_gain = self._level_to_db(volume)
        await self.coordinator._api.async_set_volume(db_gain)
        await self.coordinator.async_request_refresh()

    async def async_volume_up(self):  # type: ignore[override]
        if self.volume_level is None:
            return
        await self.async_set_volume_level(min(1.0, self.volume_level + 0.05))

    async def async_volume_down(self):  # type: ignore[override]
        if self.volume_level is None:
            return
        await self.async_set_volume_level(max(0.0, self.volume_level - 0.05))

    async def async_mute_volume(self, mute: bool):  # type: ignore[override]
        await self.coordinator._api.async_set_mute(mute)
        await self.coordinator.async_request_refresh()

    async def async_select_source(self, source: str):  # type: ignore[override]
        api_val = _SOURCE_MAP.get(source, source)
        await self.coordinator._api.async_set_source(api_val)
        await self.coordinator.async_request_refresh()

    async def async_select_sound_mode(self, sound_mode: str):  # type: ignore[override]
        if sound_mode not in _PRESET_MAP:
            _LOGGER.warning("Unknown preset option %s", sound_mode)
            return
        await self.coordinator._api.async_set_preset(_PRESET_MAP[sound_mode])
        await self.coordinator.async_request_refresh()

    # ------------------------------------------------------------
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
        _LOGGER.error("Coordinator not found during media_player setup")
        return

    async_add_entities([MiniDSPMediaPlayer(coordinator)])
