from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MiniDSPAPI
from .const import DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

# Precision for level values
# _ROUND_PRECISION = 0


class MiniDSPCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage MiniDSP data fetching and live updates."""

    def __init__(self, hass: HomeAssistant, api: MiniDSPAPI, name: str | None = None):
        super().__init__(
            hass,
            _LOGGER,
            name=name or DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self._api = api
        self._unsubscribe_ws: callable | None = None
        # Expose to entities
        self.base_url = api._base_url  # pragma: no cover
        self.address = self.base_url  # alias for clarity

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            data = await self._api.async_get_status()
            return self._rounded_levels(data)
        except Exception as err:
            raise UpdateFailed(err) from err

    # ------------------------------------------------------------------
    async def async_start(self) -> None:
        """Start listening to websocket events."""

        async def _levels_callback(event: dict[str, Any]):
            # Update only levels fields without re-fetching everything
            current = dict(self.data or {})
            updated = False
            for key in ("input_levels", "output_levels"):
                if key in event:
                    new_list = [
                        int(round(v)) if isinstance(v, (int, float)) else v
                        for v in event[key]
                    ]
                    if new_list != current.get(key):
                        current[key] = new_list
                        updated = True
            # Some versions send nested dict {"levels": {"input_levels": [...], "output_levels": [...]}}
            if "levels" in event and isinstance(event["levels"], dict):
                for key in ("input_levels", "output_levels"):
                    if key in event["levels"]:
                        new_list = [
                            int(round(v)) if isinstance(v, (int, float)) else v
                            for v in event["levels"][key]
                        ]
                        if new_list != current.get(key):
                            current[key] = new_list
                            updated = True
            if updated:
                # Push incremental update to listeners
                self.async_set_updated_data(current)

        self._unsubscribe_ws = await self._api.async_subscribe_levels(_levels_callback)

    async def async_disconnect(self):
        if self._unsubscribe_ws:
            self._unsubscribe_ws()
            self._unsubscribe_ws = None
        await self._api.async_disconnect()

    def _rounded_levels(self, data: dict[str, Any]) -> dict[str, Any]:
        def _round_val(val: Any):
            return int(round(val)) if isinstance(val, (int, float)) else val

        rounded_data: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, (list, tuple)):
                rounded_data[key] = [_round_val(v) for v in value]
            elif isinstance(value, dict):
                rounded_data[key] = {k: _round_val(v) for k, v in value.items()}
            else:
                rounded_data[key] = _round_val(value)
        return rounded_data
