from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_URL, CONF_NAME
import voluptuous as vol

from .const import DOMAIN

from homeassistant import config_entries

_LOGGER = logging.getLogger(__name__)


class MiniDSPConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the MiniDSP integration."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step where the user enters the base URL."""

        if user_input is not None:
            base_url = user_input[CONF_URL]
            title = user_input.get(CONF_NAME, base_url)

            # Use base_url as unique_id to prevent duplicates
            await self.async_set_unique_id(base_url)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title=title, data={CONF_URL: base_url})

        schema = vol.Schema({vol.Required(CONF_URL): str, vol.Optional(CONF_NAME): str})
        return self.async_show_form(step_id="user", data_schema=schema)


class MiniDSPOptionsFlow(config_entries.OptionsFlow):
    """Handle options for an existing config entry."""

    def __init__(self, entry: config_entries.ConfigEntry):
        self._entry = entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):  # type: ignore[override]
        if user_input is not None:
            # Persist new URL in options
            return self.async_create_entry(
                title="", data={CONF_URL: user_input[CONF_URL]}
            )

        current_url = self._entry.options.get(
            CONF_URL, self._entry.data.get(CONF_URL, "")
        )
        schema = vol.Schema({vol.Required(CONF_URL, default=current_url): str})
        return self.async_show_form(step_id="init", data_schema=schema)


# Hook for Home Assistant to retrieve the options flow


async def async_get_options_flow(config_entry: config_entries.ConfigEntry):  # type: ignore[override]
    return MiniDSPOptionsFlow(config_entry)
