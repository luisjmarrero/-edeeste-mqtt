"""EDEEste Home Assistant integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import EdeesteApiClient, EdeesteApiError, EdeesteAuthenticationError
from .const import (
    CONF_DISCOVERY_PREFIX,
    CONF_EMAIL,
    CONF_PASSWORD,
    DEFAULT_DISCOVERY_PREFIX,
    DOMAIN,
)
from .coordinator import EdeesteDataUpdateCoordinator

type EdeesteConfigEntry = ConfigEntry[EdeesteDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: EdeesteConfigEntry) -> bool:
    """Set up EDEEste from a config entry."""
    email = entry.options.get(CONF_EMAIL, entry.data[CONF_EMAIL])
    password = entry.options.get(CONF_PASSWORD, entry.data[CONF_PASSWORD])
    client = EdeesteApiClient(hass, email, password)
    coordinator = EdeesteDataUpdateCoordinator(
        hass,
        client,
        entry.entry_id,
        entry.options.get(CONF_DISCOVERY_PREFIX, DEFAULT_DISCOVERY_PREFIX),
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except EdeesteAuthenticationError as err:
        raise ConfigEntryNotReady(
            "EDEEste rejected the configured email or password."
        ) from err
    except EdeesteApiError as err:
        raise ConfigEntryNotReady(f"Unable to connect to EDEEste: {err}") from err

    entry.runtime_data = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EdeesteConfigEntry) -> bool:
    """Unload an EDEEste config entry."""
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when saved credentials or MQTT settings change."""
    await hass.config_entries.async_reload(entry.entry_id)
