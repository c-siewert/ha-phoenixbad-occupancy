"""Constants for the Phoenixbad integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Final

DOMAIN: Final = "phoenixbad"

# Fixed on purpose, to keep the load on the website low. Users who want a
# different schedule turn off polling and call homeassistant.update_entity.
UPDATE_INTERVAL: Final = timedelta(minutes=10)


@dataclass(frozen=True, slots=True)
class Area:
    """One bookable area of the bath."""

    key: str  # stable ID: unique IDs, option keys, device translation key
    api_area: str  # value of the `area` query parameter
    default_capacity: int  # fallback until a capacity could be derived
    default_threshold: int  # "quiet" below this many people

    @property
    def conf_threshold(self) -> str:
        return f"threshold_{self.key}"


AREAS: Final[dict[str, Area]] = {
    area.key: area
    for area in (
        Area("hallenbad", "Bad", 695, 120),
        Area("sauna", "Sauna", 300, 100),
    )
}
