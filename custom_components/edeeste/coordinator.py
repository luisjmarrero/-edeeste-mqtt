"""Polling and MQTT publication for EDEEste."""

from __future__ import annotations

import json
import logging

from homeassistant.components import mqtt
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    ConsumptionData,
    EdeesteApiClient,
    EdeesteApiError,
    EdeesteAuthenticationError,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, NAME


class EdeesteDataUpdateCoordinator(DataUpdateCoordinator[ConsumptionData]):
    """Poll EDEEste and publish each result through MQTT Discovery."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: EdeesteApiClient,
        entry_id: str,
        discovery_prefix: str,
    ) -> None:
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client
        self._device_id = f"edeeste_{entry_id}"
        self._discovery_prefix = discovery_prefix.strip("/")

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
