"""Config flow for the EDEEste integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries

from .api import EdeesteApiClient, EdeesteApiError
from .const import (
    CONF_DISCOVERY_PREFIX,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_UPDATE_TIMES,
    DEFAULT_DISCOVERY_PREFIX,
    DEFAULT_UPDATE_TIMES,
    DOMAIN,
    NAME,
    normalize_update_times,
)


class EdeesteConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle setup with EDEEste account credentials."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                user_input[CONF_UPDATE_TIMES] = normalize_update_times(
                    user_input[CONF_UPDATE_TIMES]
                )
            except ValueError:
                errors[CONF_UPDATE_TIMES] = "invalid_update_times"

            if errors:
                return self._show_user_form(user_input, errors)

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
                update_times = user_input.pop(CONF_UPDATE_TIMES, DEFAULT_UPDATE_TIMES)
                return self.async_create_entry(
                    title=NAME,
                    data=user_input,
                    options={
                        CONF_DISCOVERY_PREFIX: discovery_prefix,
                        CONF_UPDATE_TIMES: update_times,
                    },
                )

        return self._show_user_form(user_input, errors)

    def _show_user_form(
        self, user_input: dict[str, Any] | None, errors: dict[str, str]
    ) -> config_entries.ConfigFlowResult:
        """Show the setup form, retaining values after validation errors."""
        user_input = user_input or {}
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(
                        CONF_DISCOVERY_PREFIX,
                        default=user_input.get(CONF_DISCOVERY_PREFIX, DEFAULT_DISCOVERY_PREFIX),
                    ): str,
                    vol.Optional(
                        CONF_UPDATE_TIMES,
                        default=user_input.get(CONF_UPDATE_TIMES, DEFAULT_UPDATE_TIMES),
                    ): str,
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
                user_input[CONF_UPDATE_TIMES] = normalize_update_times(
                    user_input[CONF_UPDATE_TIMES]
                )
            except ValueError:
                errors[CONF_UPDATE_TIMES] = "invalid_update_times"

            if errors:
                return self._show_options_form(user_input, errors)

            try:
                await EdeesteApiClient(
                    self.hass, user_input[CONF_EMAIL], user_input[CONF_PASSWORD]
                ).async_get_consumption()
            except EdeesteApiError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="", data=user_input)

        return self._show_options_form(user_input, errors)

    def _show_options_form(
        self, user_input: dict[str, Any] | None, errors: dict[str, str]
    ) -> config_entries.ConfigFlowResult:
        """Show the options form, retaining values after validation errors."""
        user_input = user_input or {}
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_EMAIL,
                        default=user_input.get(
                            CONF_EMAIL,
                            self.config_entry.options.get(
                                CONF_EMAIL, self.config_entry.data[CONF_EMAIL]
                            ),
                        ),
                    ): str,
                    vol.Required(
                        CONF_PASSWORD,
                        default=user_input.get(
                            CONF_PASSWORD,
                            self.config_entry.options.get(
                                CONF_PASSWORD, self.config_entry.data[CONF_PASSWORD]
                            ),
                        ),
                    ): str,
                    vol.Optional(
                        CONF_DISCOVERY_PREFIX,
                        default=user_input.get(
                            CONF_DISCOVERY_PREFIX,
                            self.config_entry.options.get(
                                CONF_DISCOVERY_PREFIX, DEFAULT_DISCOVERY_PREFIX
                            ),
                        ),
                    ): str,
                    vol.Optional(
                        CONF_UPDATE_TIMES,
                        default=user_input.get(
                            CONF_UPDATE_TIMES,
                            self.config_entry.options.get(
                                CONF_UPDATE_TIMES, DEFAULT_UPDATE_TIMES
                            ),
                        ),
                    ): str,
                }
            ),
            errors=errors,
        )
