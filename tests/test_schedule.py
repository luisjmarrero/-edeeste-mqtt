"""Tests for EDEEste's configured refresh times."""

import pytest

from custom_components.edeeste.const import normalize_update_times, parse_update_times


def test_parse_update_times_sorts_and_deduplicates() -> None:
    assert normalize_update_times("18:00, 10:00, 10:00") == "10:00, 18:00"
    assert [item.isoformat() for item in parse_update_times("10:00, 18:00")] == [
        "10:00:00",
        "18:00:00",
    ]


@pytest.mark.parametrize("value", ["", "10:00,", "9:00", "24:00", "10:60"])
def test_parse_update_times_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        parse_update_times(value)
