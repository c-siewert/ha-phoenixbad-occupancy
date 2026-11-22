"""The Phoenixbad occupancy integration."""
from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PhoenixbadClient
from .coordinator import PhoenixbadConfigEntry, PhoenixbadCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: PhoenixbadConfigEntry) -> bool:
    """Set up Phoenixbad from a config entry."""
    client = PhoenixbadClient(async_get_clientsession(hass))
    coordinator = PhoenixbadCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PhoenixbadConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
