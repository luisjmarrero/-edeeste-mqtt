"""Tests for payload normalization without a Home Assistant runtime."""

from custom_components.edeeste.api import _extract_hidden_inputs, parse_consumption_payload


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
