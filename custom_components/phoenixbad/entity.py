"""Base entity for Phoenixbad."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import AreaReading
from .const import DOMAIN
from .coordinator import PhoenixbadCoordinator


class PhoenixbadEntity(CoordinatorEntity[PhoenixbadCoordinator]):
    """One entity per (area, value); each area is its own device."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: PhoenixbadCoordinator, area_key: str, description: EntityDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self.area_key = area_key
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{area_key}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{area_key}")},
            translation_key=area_key,  # device name comes from translations/*.json
            manufacturer="Phoenixbad",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://phoenixbad.de/",
        )

    @property
    def reading(self) -> AreaReading | None:
        return (self.coordinator.data or {}).get(self.area_key)

    @property
    def available(self) -> bool:
        return super().available and self.reading is not None
