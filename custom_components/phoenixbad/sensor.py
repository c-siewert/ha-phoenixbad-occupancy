"""Occupancy sensors for Phoenixbad."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .api import AreaReading
from .const import AREAS
from .coordinator import PhoenixbadConfigEntry
from .entity import PhoenixbadEntity

PARALLEL_UPDATES = 0  # coordinator does the polling


@dataclass(frozen=True, kw_only=True)
class PhoenixbadSensorDescription(SensorEntityDescription):
    value_fn: Callable[[AreaReading], StateType]


# Units for people are translated ("Personen"/"people") via translations/*.json.
SENSORS: tuple[PhoenixbadSensorDescription, ...] = (
    PhoenixbadSensorDescription(
        key="visitors",
        translation_key="visitors",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: r.visitors,
    ),
    PhoenixbadSensorDescription(
        key="free",
        translation_key="free_spots",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: r.free,
    ),
    PhoenixbadSensorDescription(
        key="occupancy",
        translation_key="occupancy",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda r: r.percent,
    ),
    PhoenixbadSensorDescription(
        key="capacity",
        translation_key="capacity",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda r: r.capacity,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: PhoenixbadConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        PhoenixbadSensor(coordinator, area_key, description)
        for area_key in AREAS
        for description in SENSORS
    )


class PhoenixbadSensor(PhoenixbadEntity, SensorEntity):
    entity_description: PhoenixbadSensorDescription

    @property
    def native_value(self) -> StateType:
        reading = self.reading
        return None if reading is None else self.entity_description.value_fn(reading)

    @property
    def extra_state_attributes(self) -> dict[str, bool] | None:
        if self.entity_description.key != "capacity" or self.reading is None:
            return None
        return {"derived_from_website": self.reading.capacity_derived}
