from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MiniDSPAPI
from .const import DOMAIN
from .coordinator import MiniDSPCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["media_player", "sensor", "switch"]


async def async_setup(hass: HomeAssistant, config: dict):  # type: ignore[arg-type]
    """YAML setup not supported."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MiniDSP from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    # Ensure we reload when options change
    entry.async_on_unload(entry.add_update_listener(_update_listener))

    base_url: str | None = entry.options.get(CONF_URL) if entry.options else None
    if not base_url:
        base_url = entry.data.get(CONF_URL)
    if not base_url:
        _LOGGER.error("Config entry missing base URL")
        raise ConfigEntryNotReady

    session = async_get_clientsession(hass)
    api = MiniDSPAPI(base_url, session)
    coordinator = MiniDSPCoordinator(hass, api, name=entry.title)

    try:
        await coordinator.async_config_entry_first_refresh()
        await coordinator.async_start()
    except Exception as err:
        raise ConfigEntryNotReady from err

    # Store
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    # Forward media_player first to make it appear first in UI entity list
    await hass.config_entries.async_forward_entry_setups(entry, ["media_player"])
    # Forward remaining platforms
    await hass.config_entries.async_forward_entry_setups(
        entry, [p for p in PLATFORMS if p != "media_player"]
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        stored = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        if stored and "coordinator" in stored:
            coordinator: MiniDSPCoordinator = stored["coordinator"]
            await coordinator.async_disconnect()

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload a config entry (triggered by HA)."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


async def _update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options/config flow updates by reloading the integration."""
    await hass.config_entries.async_reload(entry.entry_id)
