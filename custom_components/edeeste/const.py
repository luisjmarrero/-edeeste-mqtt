"""Constants for the EDEEste integration."""

from datetime import timedelta

DOMAIN = "edeeste"
NAME = "EDEEste"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_DISCOVERY_PREFIX = "discovery_prefix"
DEFAULT_DISCOVERY_PREFIX = "homeassistant"
DEFAULT_SCAN_INTERVAL = timedelta(hours=1)
DETAIL_URL = "https://oficinavirtual.edeeste.com.do/Default.aspx/GetDetalle"
LOGIN_URL = "https://oficinavirtual.edeeste.com.do/Login.aspx?ReturnUrl=%2F"

ATTRIBUTION = "Data provided by EDEEste Oficina Virtual"
