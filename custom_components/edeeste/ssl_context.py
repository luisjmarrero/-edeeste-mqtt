"""SSL context that adds the GoDaddy intermediate EDEEste's server fails to send."""

from __future__ import annotations

import ssl
from pathlib import Path

import certifi

from homeassistant.core import HomeAssistant

INTERMEDIATE_CERT = Path(__file__).parent / "godaddy_g2_intermediate.pem"

_context: ssl.SSLContext | None = None


def build_ssl_context() -> ssl.SSLContext:
    """Return a verifying context: certifi roots plus the bundled intermediate."""
    ctx = ssl.create_default_context(cafile=certifi.where())
    ctx.load_verify_locations(cafile=str(INTERMEDIATE_CERT))
    return ctx


async def async_get_ssl_context(hass: HomeAssistant) -> ssl.SSLContext:
    """Build the context once, off the event loop (loading certs does file I/O)."""
    global _context
    if _context is None:
        _context = await hass.async_add_executor_job(build_ssl_context)
    return _context
