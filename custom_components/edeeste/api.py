"""Client for EDEEste's Oficina Virtual consumption endpoint."""

from __future__ import annotations

import json
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .const import DETAIL_URL, LOGIN_URL


class EdeesteApiError(Exception):
    """Base error for EDEEste API failures."""


class EdeesteAuthenticationError(EdeesteApiError):
    """The supplied EDEEste session is not authenticated."""


@dataclass(frozen=True, slots=True)
class ConsumptionData:
    """Consumption values returned by Oficina Virtual."""

    current_consumption: float | int | None
    projected_consumption: float | int | None
    previous_consumption: float | int | None
    days_consumption: int | None
    nic: str | None
    current_consumption_date: str | None
    last_reading_date: str | None
    previous_bill_date: str | None
    message: str | None


class EdeesteApiClient:
    """Fetch consumption data using a fresh authenticated EDEEste session."""

    def __init__(self, hass: HomeAssistant, email: str, password: str) -> None:
        self._session = async_create_clientsession(hass)
        self._email = email
        self._password = password
        self._authenticated = False

    async def async_get_consumption(self) -> ConsumptionData:
        """Return the current account's consumption summary."""
        if not self._authenticated:
            await self._async_login()
        try:
            return await self._async_fetch_consumption()
        except EdeesteAuthenticationError:
            self._authenticated = False
            await self._async_login()
            return await self._async_fetch_consumption()

    async def _async_fetch_consumption(self) -> ConsumptionData:
        """Retrieve details, raising an auth error for an expired session."""
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/json; charset=utf-8",
            "X-Requested-With": "XMLHttpRequest",
        }
        try:
            async with self._session.get(DETAIL_URL, headers=headers) as response:
                if response.status in (401, 403):
                    raise EdeesteAuthenticationError("EDEEste rejected the authenticated session")
                response.raise_for_status()
                if "Login.aspx" in str(response.url):
                    raise EdeesteAuthenticationError("EDEEste session has expired")
                payload: Any = await response.json(content_type=None)
        except aiohttp.ClientResponseError as err:
            raise EdeesteApiError(f"EDEEste returned HTTP {err.status}") from err
        except aiohttp.ClientError as err:
            raise EdeesteApiError("Unable to reach EDEEste") from err
        except (TypeError, ValueError, json.JSONDecodeError) as err:
            raise EdeesteAuthenticationError(
                "EDEEste returned a non-JSON response; the session may have expired"
            ) from err

        return parse_consumption_payload(payload)

    async def _async_login(self) -> None:
        """Create a session by submitting the ASP.NET login form."""
        try:
            async with self._session.get(LOGIN_URL) as response:
                response.raise_for_status()
                form = _extract_hidden_inputs(await response.text())
            form.update(
                {
                    "ctl00$ContentPlaceHolder1$ucLogin$TxtUsuario": self._email,
                    "ctl00$ContentPlaceHolder1$ucLogin$TxtPassword": self._password,
                    "ctl00$ContentPlaceHolder1$ucLogin$BtnLogin": "Iniciar sesión",
                }
            )
            async with self._session.post(LOGIN_URL, data=form) as response:
                response.raise_for_status()
                if "Login.aspx" in str(response.url):
                    raise EdeesteAuthenticationError("EDEEste rejected the email or password")
        except EdeesteAuthenticationError:
            raise
        except aiohttp.ClientError as err:
            raise EdeesteApiError("Unable to reach EDEEste") from err
        self._authenticated = True


def parse_consumption_payload(payload: Any) -> ConsumptionData:
    """Validate and normalize the ASP.NET JSON response."""
    result = payload.get("d") if isinstance(payload, dict) else None
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except json.JSONDecodeError as err:
            raise EdeesteApiError("EDEEste returned an invalid data payload") from err
    if not isinstance(result, list) or not result or not isinstance(result[0], dict):
        raise EdeesteApiError("EDEEste returned no consumption data")

    item = result[0]
    return ConsumptionData(
        current_consumption=item.get("ConsumoMesActual"),
        projected_consumption=item.get("Proyectado"),
        previous_consumption=item.get("ConsumoMesAnterior"),
        days_consumption=item.get("DiasConsumo"),
        nic=_as_string(item.get("NicTelemedido")),
        current_consumption_date=_as_string(item.get("FechaConsumoMesActual")),
        last_reading_date=_as_string(item.get("FechaUltimaLectura")),
        previous_bill_date=_as_string(item.get("FechaFacturaMesAnterior")),
        message=_as_string(item.get("MensajeConsumo") or item.get("Msj")),
    )


def _as_string(value: Any) -> str | None:
    return str(value) if value is not None else None


class _HiddenInputParser(HTMLParser):
    """Extract ASP.NET state fields without adding an HTML parsing dependency."""

    def __init__(self) -> None:
        super().__init__()
        self.values: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "input":
            return
        attributes = dict(attrs)
        if attributes.get("type") == "hidden" and attributes.get("name"):
            self.values[attributes["name"]] = attributes.get("value", "")


def _extract_hidden_inputs(page: str) -> dict[str, str]:
    """Return state fields required by the ASP.NET login POST."""
    parser = _HiddenInputParser()
    parser.feed(page)
    if "__VIEWSTATE" not in parser.values:
        raise EdeesteApiError("EDEEste login page did not include its form state")
    return parser.values
