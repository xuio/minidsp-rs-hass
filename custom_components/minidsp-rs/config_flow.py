from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_URL, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector
import voluptuous as vol

from .const import (
    CONF_POLL_INTERVAL,
    CONF_SERVER_UPDATES,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_SERVER_UPDATES,
    DOMAIN,
    POLL_INTERVALS,
    SERVER_UPDATES,
)

from homeassistant import config_entries

_LOGGER = logging.getLogger(__name__)


class MiniDSPConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the MiniDSP integration."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> MiniDSPOptionsFlow:
        """Return the options flow handler."""
        return MiniDSPOptionsFlow(config_entry)

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
            return self.async_create_entry(title="", data=user_input)

        options = self._entry.options
        current_url = options.get(CONF_URL, self._entry.data.get(CONF_URL, ""))
        schema = vol.Schema(
            {
                vol.Required(CONF_URL, default=current_url): str,
                vol.Required(
                    CONF_SERVER_UPDATES,
                    default=options.get(CONF_SERVER_UPDATES, DEFAULT_SERVER_UPDATES),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=SERVER_UPDATES,
                        translation_key=CONF_SERVER_UPDATES,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_POLL_INTERVAL,
                    default=options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=POLL_INTERVALS,
                        translation_key=CONF_POLL_INTERVAL,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
