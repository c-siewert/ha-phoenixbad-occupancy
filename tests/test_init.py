"""Tests for the Phoenixbad integration."""
import logging

import aiohttp
import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.phoenixbad.api import URL, parse_area
from custom_components.phoenixbad.const import DOMAIN

POOL_VISITORS = "sensor.phoenixbad_indoor_pool_visitors"
SAUNA_VISITORS = "sensor.phoenixbad_sauna_visitors"


def snippet(free: int, pct: str) -> str:
    return (
        f'<div class="live-visitors" data-free="{free}">'
        f'<div class="bar" style="width: {pct}%;"></div></div>'
    )


POOL_OK = snippet(544, "21.73")  # 151 of 695
SAUNA_OK = snippet(245, "18.33")  # 55 of 300


def mock_site(
    aioclient_mock: AiohttpClientMocker,
    bad: str | Exception = POOL_OK,
    sauna: str | Exception = SAUNA_OK,
) -> None:
    aioclient_mock.clear_requests()
    for area, response in (("Bad", bad), ("Sauna", sauna)):
        params = {"action": "updateLiveVisitors", "area": area}
        if isinstance(response, Exception):
            aioclient_mock.get(URL, params=params, exc=response)
        else:
            aioclient_mock.get(URL, params=params, text=response)


async def setup_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="Phoenixbad")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def refresh(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


# --- Parsing ---------------------------------------------------------------


def test_parse_derives_capacity():
    r = parse_area(snippet(544, "21.73"), 695)
    assert (r.free, r.capacity, r.visitors, r.capacity_derived) == (544, 695, 151, True)


def test_parse_full_falls_back():
    r = parse_area(snippet(0, "100"), 300)
    assert (r.capacity, r.visitors, r.capacity_derived) == (300, 300, False)


def test_parse_nearly_full_falls_back():
    # 681 of 695: deriving would give 697 because the % is rounded.
    r = parse_area(snippet(14, "97.99"), 695)
    assert (r.capacity, r.visitors, r.percent, r.capacity_derived) == (695, 681, 97.99, False)


def test_parse_without_percent():
    r = parse_area('<div data-free="250"></div>', 300)
    assert (r.visitors, r.percent) == (50, 16.67)


# --- Config flow -----------------------------------------------------------


async def test_config_flow(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_site(aioclient_mock)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.parametrize(
    ("response", "error"),
    [
        ("<p>Wartung</p>", "invalid_response"),
        (aiohttp.ClientError(), "cannot_connect"),
        (TimeoutError(), "cannot_connect"),
    ],
)
async def test_config_flow_error_recovers(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    response: str | Exception,
    error: str,
):
    mock_site(aioclient_mock, bad=response)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}

    mock_site(aioclient_mock)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_config_flow_single_instance(hass: HomeAssistant):
    MockConfigEntry(domain=DOMAIN, title="Phoenixbad").add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


# --- Setup and entities ----------------------------------------------------


async def test_entities(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_site(aioclient_mock)
    entry = await setup_entry(hass)
    assert entry.state is ConfigEntryState.LOADED

    pool = hass.states.get(POOL_VISITORS)
    assert pool.state == "151"
    assert pool.attributes["unit_of_measurement"] == "people"
    assert hass.states.get(SAUNA_VISITORS).state == "55"
    assert hass.states.get("binary_sensor.phoenixbad_indoor_pool_quiet").state == "off"  # 151 >= 120
    assert hass.states.get("binary_sensor.phoenixbad_sauna_quiet").state == "on"  # 55 < 100


async def test_entity_ids_german(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    hass.config.language = "de"
    mock_site(aioclient_mock)
    await setup_entry(hass)
    assert hass.states.get("sensor.phoenixbad_hallenbad_besucher").state == "151"
    assert hass.states.get("binary_sensor.phoenixbad_sauna_ruhig").state == "on"


async def test_setup_retries_when_unreachable(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
):
    mock_site(aioclient_mock, bad=aiohttp.ClientError(), sauna=aiohttp.ClientError())
    entry = MockConfigEntry(domain=DOMAIN, title="Phoenixbad")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_one_area_down(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, caplog: pytest.LogCaptureFixture
):
    caplog.set_level(logging.INFO, logger="custom_components.phoenixbad")
    mock_site(aioclient_mock, sauna="")
    entry = await setup_entry(hass)
    assert hass.states.get(POOL_VISITORS).state == "151"
    assert hass.states.get(SAUNA_VISITORS).state == "unavailable"

    await refresh(hass, entry)  # still down: logged only once
    assert caplog.text.count("Phoenixbad sauna is unavailable") == 1

    mock_site(aioclient_mock)
    await refresh(hass, entry)
    assert hass.states.get(SAUNA_VISITORS).state == "55"
    assert caplog.text.count("Phoenixbad sauna is available again") == 1


async def test_keeps_last_derived_capacity(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
):
    mock_site(aioclient_mock, bad=snippet(600, "14.29"))  # capacity raised to 700
    entry = await setup_entry(hass)
    assert hass.states.get("sensor.phoenixbad_indoor_pool_capacity").state == "700"

    mock_site(aioclient_mock, bad=snippet(10, "98.57"))  # too full to derive
    await refresh(hass, entry)
    capacity = hass.states.get("sensor.phoenixbad_indoor_pool_capacity")
    assert capacity.state == "700"  # not the default 695
    assert capacity.attributes["derived_from_website"] is False
    assert hass.states.get(POOL_VISITORS).state == "690"


async def test_options_reload(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker):
    mock_site(aioclient_mock)
    entry = await setup_entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"threshold_hallenbad": 200, "threshold_sauna": 100}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {"threshold_hallenbad": 200, "threshold_sauna": 100}
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.phoenixbad_indoor_pool_quiet").state == "on"  # 151 < 200
