"""Allow unit tests to import the integration without Home Assistant installed."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from typing import Any


def _ensure_module(name: str) -> ModuleType:
    module = sys.modules.get(name)
    if module is None:
        module = ModuleType(name)
        sys.modules[name] = module
    return module


def _install_home_assistant_stubs() -> None:
    """Stub the Home Assistant modules imported by the integration package."""
    _ensure_module("homeassistant")

    config_entries = _ensure_module("homeassistant.config_entries")

    class ConfigEntry:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __class_getitem__(cls, item: Any) -> type:
            return cls

    class ConfigFlow:
        pass

    class OptionsFlow:
        pass

    config_entries.ConfigEntry = ConfigEntry
    config_entries.ConfigFlow = ConfigFlow
    config_entries.OptionsFlow = OptionsFlow
    config_entries.ConfigFlowResult = Any

    core = _ensure_module("homeassistant.core")
    core.HomeAssistant = object

    exceptions = _ensure_module("homeassistant.exceptions")

    class ConfigEntryNotReady(Exception):
        pass

    exceptions.ConfigEntryNotReady = ConfigEntryNotReady

    helpers = _ensure_module("homeassistant.helpers")
    aiohttp_client = _ensure_module("homeassistant.helpers.aiohttp_client")
    aiohttp_client.async_create_clientsession = lambda *args, **kwargs: None

    event = _ensure_module("homeassistant.helpers.event")
    event.async_track_point_in_time = lambda *args, **kwargs: lambda: None

    update_coordinator = _ensure_module("homeassistant.helpers.update_coordinator")

    class DataUpdateCoordinator:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __class_getitem__(cls, item: Any) -> type:
            return cls

    class UpdateFailed(Exception):
        pass

    update_coordinator.DataUpdateCoordinator = DataUpdateCoordinator
    update_coordinator.UpdateFailed = UpdateFailed

    util = _ensure_module("homeassistant.util")
    dt = _ensure_module("homeassistant.util.dt")
    dt.as_utc = lambda value: value
    dt.now = lambda *args, **kwargs: None

    components = _ensure_module("homeassistant.components")
    mqtt = _ensure_module("homeassistant.components.mqtt")
    mqtt.async_publish = lambda *args, **kwargs: None

    aiohttp = _ensure_module("aiohttp")

    class ClientError(Exception):
        pass

    class ClientResponseError(ClientError):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args)
            self.status = kwargs.get("status", 0)

    aiohttp.ClientError = ClientError
    aiohttp.ClientResponseError = ClientResponseError


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_install_home_assistant_stubs()
