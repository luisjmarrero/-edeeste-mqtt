"""Config flow for the EDEEste integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries

from .api import EdeesteApiClient, EdeesteApiError
from .const import CONF_DISCOVERY_PREFIX, CONF_EMAIL, CONF_PASSWORD, DEFAULT_DISCOVERY_PREFIX, DOMAIN, NAME


class EdeesteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle setup with EDEEste account credentials."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await EdeesteApiClient(
                    self.hass, user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
                ).async_get_consumption()
            except EdeesteApiError:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                discovery_prefix = user_input.pop(CONF_DISCOVERY_PREFIX, DEFAULT_DISCOVERY_PREFIX)
                return self.async_create_entry(
                    title=NAME,
                    data=user_input,
                    options={CONF_DISCOVERY_PREFIX: discovery_prefix},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_DISCOVERY_PREFIX, default=DEFAULT_DISCOVERY_PREFIX): str,
                }
            ),
            errors=errors,
            description_placeholders={
                "instructions": "Sign in with the email and password for your EDEEste Oficina Virtual account."
            },
        )

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> EdeesteOptionsFlow:
        return EdeesteOptionsFlow()


class EdeesteOptionsFlow(config_entries.OptionsFlow):
    """Allow replacing EDEEste account credentials."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                await EdeesteApiClient(
                    self.hass, user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
                ).async_get_consumption()
            except EdeesteApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(
                        CONF_DISCOVERY_PREFIX,
                        default=self.config_entry.options.get(
                            CONF_DISCOVERY_PREFIX, DEFAULT_DISCOVERY_PREFIX
                        ),
                    ): str,
                }
            ),
            errors=errors,
        )
