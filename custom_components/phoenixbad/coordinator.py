"""Data update coordinator for Phoenixbad."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AreaReading, PhoenixbadClient, PhoenixbadError
from .const import AREAS, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

type PhoenixbadData = dict[str, AreaReading | None]


class PhoenixbadCoordinator(DataUpdateCoordinator[PhoenixbadData]):
    """Polls both areas in one go."""

    config_entry: PhoenixbadConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: PhoenixbadConfigEntry, client: PhoenixbadClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        # Last capacity derived from the website, used while it can't be
        # derived (nearly full). Starts at the defaults.
        self._capacity = {key: area.default_capacity for key, area in AREAS.items()}
        # Areas that failed while the others worked; for logging only.
        self._unavailable: set[str] = set()

    async def _async_update_data(self) -> PhoenixbadData:
        results = await asyncio.gather(
            *(
                self.client.async_get_area(area.api_area, self._capacity[key])
                for key, area in AREAS.items()
            ),
            return_exceptions=True,
        )
        data: PhoenixbadData = {}
        errors: dict[str, PhoenixbadError] = {}
        for key, result in zip(AREAS, results, strict=True):
            if isinstance(result, PhoenixbadError):
                errors[key] = result
                data[key] = None
            elif isinstance(result, BaseException):
                raise result
            else:
                data[key] = result
                if result.capacity_derived:
                    self._capacity[key] = result.capacity

        if len(errors) == len(AREAS):
            # The coordinator itself logs this once, and again on recovery.
            raise UpdateFailed(f"Phoenixbad not reachable: {next(iter(errors.values()))}")

        # One area failing only makes its own entities unavailable: log once
        # when it goes and once when it comes back.
        for key in AREAS:
            if key in errors and key not in self._unavailable:
                _LOGGER.info("Phoenixbad %s is unavailable: %s", key, errors[key])
                self._unavailable.add(key)
            elif key not in errors and key in self._unavailable:
                _LOGGER.info("Phoenixbad %s is available again", key)
                self._unavailable.discard(key)
        return data


type PhoenixbadConfigEntry = ConfigEntry[PhoenixbadCoordinator]
