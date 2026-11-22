"""Minimal client for the Phoenixbad live-visitor endpoint.

The endpoint returns an HTML snippet like
    <div ... data-free="544"><div ... style="width: 21.73%;">
i.e. the number of free spots and the fill level in percent.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import re

import aiohttp

URL = "https://phoenixbad.de/wp-admin/admin-ajax.php"
HEADERS = {
    "User-Agent": "HomeAssistant-Phoenixbad/0.1 (+https://www.home-assistant.io)",
    "Referer": "https://phoenixbad.de/",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "text/html, */*; q=0.01",
}
TIMEOUT = 20

_FREE_RE = re.compile(r'data-free\s*=\s*"(\d+)"')
_PCT_RE = re.compile(r"width:\s*([0-9]+(?:[.,][0-9]+)?)\s*%")

# The website rounds the fill level to 2 decimals. That rounding error is
# amplified by 1 / (1 - fill level) when deriving the capacity; for ~700 spots
# it stays below 0.5 (so rounding still lands on the exact capacity) only up
# to ~93 %. 90 % leaves some margin.
MAX_DERIVE_PERCENT = 90


class PhoenixbadError(Exception):
    """Base error."""


class PhoenixbadConnectionError(PhoenixbadError):
    """The website could not be reached."""


class PhoenixbadParseError(PhoenixbadError):
    """The response did not contain the expected values."""


@dataclass(frozen=True, slots=True)
class AreaReading:
    """One reading for one area."""

    free: int
    percent: float
    capacity: int
    capacity_derived: bool  # False -> fallback capacity was used

    @property
    def visitors(self) -> int:
        return max(self.capacity - self.free, 0)


def derive_capacity(free: int, percent: float | None, fallback: int) -> tuple[int, bool]:
    """Capacity implied by free spots and fill level: free / (1 - percent).

    Deriving it (instead of hard-coding it) means a capacity change on the
    website shows up as a changed value rather than silently skewing visitors.
    Above MAX_DERIVE_PERCENT the formula is too imprecise, so fall back there.
    """
    if percent is None or not 0 <= percent <= MAX_DERIVE_PERCENT:
        return max(fallback, free), False
    capacity = round(free / (1 - percent / 100))
    if capacity <= 0 or capacity < free:
        return max(fallback, free), False
    return capacity, True


def parse_area(html: str, fallback_capacity: int) -> AreaReading:
    """Parse the HTML snippet returned for one area.

    `fallback_capacity` is used when the capacity can't be derived from this
    reading; ideally the last derived one, else a default.
    """
    free_match = _FREE_RE.search(html)
    if free_match is None:
        raise PhoenixbadParseError("no data-free attribute in response")
    free = int(free_match.group(1))

    pct_match = _PCT_RE.search(html)
    percent = float(pct_match.group(1).replace(",", ".")) if pct_match else None

    capacity, derived = derive_capacity(free, percent, fallback_capacity)
    if percent is None:
        percent = round(100 * (capacity - free) / capacity, 2) if capacity else 0.0
    return AreaReading(free, percent, capacity, derived)


class PhoenixbadClient:
    """Fetches readings from phoenixbad.de."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def async_get_area(self, api_area: str, fallback_capacity: int) -> AreaReading:
        params = {"action": "updateLiveVisitors", "area": api_area}
        try:
            async with asyncio.timeout(TIMEOUT):
                async with self._session.get(URL, params=params, headers=HEADERS) as resp:
                    resp.raise_for_status()
                    html = await resp.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise PhoenixbadConnectionError(f"{api_area}: {err}") from err
        return parse_area(html, fallback_capacity)
