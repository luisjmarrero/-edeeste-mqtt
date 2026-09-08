"""Polling and MQTT publication for EDEEste."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable
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
    ServiceStatusData,
)
from .const import DOMAIN, NAME, UPDATE_TIME_ZONE, parse_update_times


@dataclass(frozen=True, slots=True)
class EdeesteData:
    """Bundle of everything published to MQTT for one refresh cycle."""

    consumption: ConsumptionData
    service_status: ServiceStatusData | None


class EdeesteDataUpdateCoordinator(DataUpdateCoordinator[EdeesteData]):
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

    async def _async_update_data(self) -> EdeesteData:
        try:
            consumption = await self.client.async_get_consumption()
        except EdeesteAuthenticationError:
            raise
        except EdeesteApiError as err:
            raise UpdateFailed(err) from err

        service_status = await self._async_get_service_status(consumption)
        data = EdeesteData(consumption=consumption, service_status=service_status)
        await self._async_publish_mqtt(data)
        return data

    async def _async_get_service_status(
        self, consumption: ConsumptionData
    ) -> ServiceStatusData | None:
        """Fetch the circuit status, degrading gracefully if it fails."""
        if not consumption.nic:
            self.logger.debug("Skipping EDEEste circuit status: no NIC in consumption data")
            return None
        try:
            return await self.client.async_get_service_status(consumption.nic)
        except (EdeesteApiError, EdeesteAuthenticationError) as err:
            self.logger.warning("Skipping EDEEste circuit status this cycle: %s", err)
            return None

    async def _async_publish_mqtt(self, data: EdeesteData) -> None:
        """Publish retained discovery configs, states, and account attributes."""
        consumption = data.consumption
        device = {
            "identifiers": [self._device_id],
            "manufacturer": "EDEEste",
            "model": "Oficina Virtual",
            "name": f"EDEEste account {consumption.nic or 'unknown'}",
        }
        attributes = {
            "nic": consumption.nic,
            "current_consumption_date": consumption.current_consumption_date,
            "last_reading_date": consumption.last_reading_date,
            "previous_bill_date": consumption.previous_bill_date,
            "message": consumption.message,
        }
        sensors = (
            ("current_consumption", "Current consumption", consumption.current_consumption, "kWh", "energy"),
            ("projected_consumption", "Projected consumption", consumption.projected_consumption, "kWh", "energy"),
            ("previous_consumption", "Previous consumption", consumption.previous_consumption, "kWh", "energy"),
            ("days_consumption", "Consumption days", consumption.days_consumption, "d", None),
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

        if data.service_status is not None:
            await self._async_publish_service_status(device, data.service_status)

    async def _async_publish_service_status(
        self, device: dict[str, Any], status: ServiceStatusData
    ) -> None:
        """Publish the circuit/service incident binary sensor.

        Skipped entirely on a failed fetch (see ``_async_get_service_status``),
        which leaves any previously retained MQTT state in place rather than
        publishing a stale or unknown value.
        """
        key = "service_incident"
        base = f"{self._discovery_prefix}/binary_sensor/{self._device_id}/{key}"
        config = {
            "name": "Service incident",
            "unique_id": f"{self._device_id}_{key}",
            "state_topic": f"{base}/state",
            "json_attributes_topic": f"{base}/attributes",
            "device_class": "problem",
            "payload_on": "ON",
            "payload_off": "OFF",
            "device": device,
            "origin": {"name": NAME, "sw_version": "0.1.0"},
        }
        state = "OFF" if status.sin_incidencia else "ON"
        attributes = {"nic": status.nic, "message": status.message}
        await mqtt.async_publish(self.hass, f"{base}/config", json.dumps(config), retain=True)
        await mqtt.async_publish(self.hass, f"{base}/state", state, retain=True)
        await mqtt.async_publish(
            self.hass, f"{base}/attributes", json.dumps(attributes), retain=True
        )