"""Tests for payload normalization without a Home Assistant runtime."""

import pytest

from custom_components.edeeste.api import (
    EdeesteApiError,
    _extract_hidden_inputs,
    parse_consumption_payload,
    parse_service_status_payload,
)


def test_parse_consumption_payload() -> None:
    data = parse_consumption_payload(
        {
            "d": [
                {
                    "ConsumoMesActual": 438,
                    "Proyectado": 105,
                    "ConsumoMesAnterior": 505,
                    "DiasConsumo": 7,
                    "NicTelemedido": "1234567",
                    "FechaUltimaLectura": "2026-08-26",
                }
            ]
        }
    )

    assert data.current_consumption == 438
    assert data.projected_consumption == 105
    assert data.previous_consumption == 505
    assert data.days_consumption == 7
    assert data.nic == "1234567"
    assert data.last_reading_date == "2026-08-26"


def test_extract_hidden_inputs() -> None:
    fields = _extract_hidden_inputs(
        '<input type="hidden" name="__VIEWSTATE" value="state">'
        '<input type="hidden" name="__EVENTVALIDATION" value="validation">'
    )

    assert fields == {"__VIEWSTATE": "state", "__EVENTVALIDATION": "validation"}


def test_parse_service_status_payload_no_incident() -> None:
    status = parse_service_status_payload(
        {"d": {"Nic": "1234567", "SinIncidencia": True, "Error": False, "Mensaje": "Sin incidencias"}}
    )

    assert status.nic == "1234567"
    assert status.sin_incidencia is True
    assert status.message == "Sin incidencias"


def test_parse_service_status_payload_incident() -> None:
    status = parse_service_status_payload(
        {"d": {"Nic": "1234567", "SinIncidencia": False, "Error": False, "Mensaje": "Interrupcion programada"}}
    )

    assert status.sin_incidencia is False
    assert status.message == "Interrupcion programada"


def test_parse_service_status_payload_missing_field_defaults_to_incident() -> None:
    status = parse_service_status_payload({"d": {"Nic": "1234567"}})

    assert status.sin_incidencia is False


def test_parse_service_status_payload_error_raises() -> None:
    with pytest.raises(EdeesteApiError, match="NIC invalido"):
        parse_service_status_payload(
            {"d": {"Error": True, "Mensaje": "NIC invalido"}}
        )