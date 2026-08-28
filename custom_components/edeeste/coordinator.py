"""Polling and MQTT publication for EDEEste."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    ConsumptionData,
    EdeesteApiClient,
    EdeesteApiError,
    EdeesteAuthenticationError,
)
from .const import DOMAIN, NAME, UPDATE_TIME_ZONE, parse_update_times


class EdeesteDataUpdateCoordinator(DataUpdateCoordinator[ConsumptionData]):
    """Poll EDEEste and publish each result through MQTT Discovery."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: EdeesteApiClient,
        entry_id: str,
        discovery_prefix: str,
        update_times: str,
    ) -> None:
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name=DOMAIN,
            update_interval=None,
        )
        self.client = client
        self._device_id = f"edeeste_{entry_id}"
        self._discovery_prefix = discovery_prefix.strip("/")
        self._update_times = parse_update_times(update_times)
        self._time_zone = ZoneInfo(UPDATE_TIME_ZONE)
        self._cancel_scheduled_refresh: Callable[[], None] | None = None

    def async_start_schedule(self) -> None:
        """Start the daily refresh schedule after the initial data load."""
        self._async_schedule_next_refresh()

    def async_stop_schedule(self) -> None:
        """Cancel the next refresh when the config entry is unloaded."""
        if self._cancel_scheduled_refresh is not None:
            self._cancel_scheduled_refresh()
            self._cancel_scheduled_refresh = None

    def _async_schedule_next_refresh(self) -> None:
        """Schedule the nearest configured update time in AST."""
        now = dt_util.now(self._time_zone)
        candidates = [
            datetime.combine(now.date(), update_time, tzinfo=self._time_zone)
            for update_time in self._update_times
        ]
        next_refresh = next((item for item in candidates if item > now), None)
        if next_refresh is None:
            next_refresh = candidates[0] + timedelta(days=1)

        self._cancel_scheduled_refresh = async_track_point_in_time(
            self.hass, self._async_scheduled_refresh, dt_util.as_utc(next_refresh)
        )

    async def _async_scheduled_refresh(self, _: datetime) -> None:
        """Refresh data and arrange the following configured refresh."""
        self._cancel_scheduled_refresh = None
        self._async_schedule_next_refresh()
        await self.async_request_refresh()

    async def _async_update_data(self) -> ConsumptionData:
        try:
            data = await self.client.async_get_consumption()
            await self._async_publish_mqtt(data)
            return data
        except EdeesteAuthenticationError:
            raise
        except EdeesteApiError as err:
            raise UpdateFailed(err) from err

    async def _async_publish_mqtt(self, data: ConsumptionData) -> None:
        """Publish retained discovery configs, states, and account attributes."""
        device = {
            "identifiers": [self._device_id],
            "manufacturer": "EDEEste",
            "model": "Oficina Virtual",
            "name": f"EDEEste account {data.nic or 'unknown'}",
        }
        attributes = {
            "nic": data.nic,
            "current_consumption_date": data.current_consumption_date,
            "last_reading_date": data.last_reading_date,
            "previous_bill_date": data.previous_bill_date,
            "message": data.message,
        }
        sensors = (
            ("current_consumption", "Current consumption", data.current_consumption, "kWh", "energy"),
            ("projected_consumption", "Projected consumption", data.projected_consumption, "kWh", "energy"),
            ("previous_consumption", "Previous consumption", data.previous_consumption, "kWh", "energy"),
            ("days_consumption", "Consumption days", data.days_consumption, "d", None),
        )
        for key, name, value, unit, device_class in sensors:
            base = f"{self._discovery_prefix}/sensor/{self._device_id}/{key}"
            config = {
                "name": name,
                "unique_id": f"{self._device_id}_{key}",
                "state_topic": f"{base}/state",
                "json_attributes_topic": f"{base}/attributes",
                "unit_of_measurement": unit,
                "state_class": "measurement",
                "device": device,
                "origin": {"name": NAME, "sw_version": "0.1.0"},
            }
            if device_class:
                config["device_class"] = device_class
            await mqtt.async_publish(self.hass, f"{base}/config", json.dumps(config), retain=True)
            await mqtt.async_publish(self.hass, f"{base}/state", str(value), retain=True)
            await mqtt.async_publish(
                self.hass, f"{base}/attributes", json.dumps(attributes), retain=True
            )
