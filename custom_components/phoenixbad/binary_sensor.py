"""'Quiet' binary sensors: on while visitors are below the configured threshold."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import AREAS
from .coordinator import PhoenixbadConfigEntry, PhoenixbadCoordinator
from .entity import PhoenixbadEntity

PARALLEL_UPDATES = 0

QUIET = BinarySensorEntityDescription(key="quiet", translation_key="quiet")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PhoenixbadConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(PhoenixbadQuietSensor(coordinator, key) for key in AREAS)


class PhoenixbadQuietSensor(PhoenixbadEntity, BinarySensorEntity):
    def __init__(self, coordinator: PhoenixbadCoordinator, area_key: str) -> None:
        super().__init__(coordinator, area_key, QUIET)
        area = AREAS[area_key]
        self._threshold = int(
            coordinator.config_entry.options.get(area.conf_threshold, area.default_threshold)
        )
        self._attr_extra_state_attributes = {"threshold": self._threshold}

    @property
    def is_on(self) -> bool | None:
        reading = self.reading
        return None if reading is None else reading.visitors < self._threshold
