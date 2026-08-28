"""Constants for the EDEEste integration."""

from datetime import time
import re

DOMAIN = "edeeste"
NAME = "EDEEste"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_DISCOVERY_PREFIX = "discovery_prefix"
CONF_UPDATE_TIMES = "update_times"
DEFAULT_DISCOVERY_PREFIX = "homeassistant"
DEFAULT_UPDATE_TIMES = "10:00"
UPDATE_TIME_ZONE = "America/Santo_Domingo"
DETAIL_URL = "https://oficinavirtual.edeeste.com.do/Default.aspx/GetDetalle"
LOGIN_URL = "https://oficinavirtual.edeeste.com.do/Login.aspx?ReturnUrl=%2F"

ATTRIBUTION = "Data provided by EDEEste Oficina Virtual"


def parse_update_times(value: str) -> tuple[time, ...]:
    """Parse a comma-separated list of daily AST update times.

    Values are kept in chronological order so an equivalent configuration is
    always stored the same way.
    """
    if not isinstance(value, str):
        raise ValueError("Update times must be text")

    values = [item.strip() for item in value.split(",")]
    if not values or any(not item or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", item) for item in values):
        raise ValueError("Update times must use the HH:MM format")

    parsed = tuple(sorted({time.fromisoformat(item) for item in values}))
    if not parsed:
        raise ValueError("At least one update time is required")
    return parsed


def normalize_update_times(value: str) -> str:
    """Return update times in their canonical, comma-separated form."""
    return ", ".join(item.strftime("%H:%M") for item in parse_update_times(value))
