"""Tests for the coordinator's circuit-status fetch behavior."""

from __future__ import annotations

import asyncio
import logging

from custom_components.edeeste.api import ConsumptionData, EdeesteApiError, ServiceStatusData
from custom_components.edeeste.coordinator import EdeesteDataUpdateCoordinator


class _FakeClient:
    """Stub client that returns or raises whatever a test needs."""

    def __init__(self, *, service_status: ServiceStatusData | None = None, error: Exception | None = None) -> None:
        self._service_status = service_status
        self._error = error

    async def async_get_service_status(self, nic: str) -> ServiceStatusData | None:
        if self._error is not None:
            raise self._error
        return self._service_status


def _make_coordinator(client: _FakeClient) -> EdeesteDataUpdateCoordinator:
    """Build a coordinator without running __init__ (no real hass needed)."""
    coordinator = object.__new__(EdeesteDataUpdateCoordinator)
    coordinator.client = client
    coordinator.logger = logging.getLogger("test")
    return coordinator


def _consumption(nic: str | None) -> ConsumptionData:
    return ConsumptionData(
        current_consumption=1,
        projected_consumption=1,
        previous_consumption=1,
        days_consumption=1,
        nic=nic,
        current_consumption_date=None,
        last_reading_date=None,
        previous_bill_date=None,
        message=None,
    )


def test_service_status_returns_data_on_success() -> None:
    status = ServiceStatusData(nic="123", sin_incidencia=True, message="Sin incidencias")
    coordinator = _make_coordinator(_FakeClient(service_status=status))

    result = asyncio.run(coordinator._async_get_service_status(_consumption("123")))

    assert result is status


def test_service_status_degrades_gracefully_on_api_error() -> None:
    coordinator = _make_coordinator(_FakeClient(error=EdeesteApiError("boom")))

    result = asyncio.run(coordinator._async_get_service_status(_consumption("123")))

    assert result is None


def test_service_status_skipped_when_consumption_has_no_nic() -> None:
    coordinator = _make_coordinator(_FakeClient(service_status=ServiceStatusData(nic=None, sin_incidencia=True, message=None)))

    result = asyncio.run(coordinator._async_get_service_status(_consumption(None)))

    assert result is None