"""Tests for Ariston config flow / options flow."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_PASSWORD, CONF_SCAN_INTERVAL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ariston.const import (
    API_URL_SETTING,
    API_USER_AGENT,
    BUS_ERRORS_SCAN_INTERVAL,
    DOMAIN,
    ENERGY_SCAN_INTERVAL,
)


@pytest.fixture
def mock_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a registered MockConfigEntry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="GW123",
        title="Ariston",
        data={
            CONF_USERNAME: "u",
            CONF_PASSWORD: "p",
            API_URL_SETTING: "https://example",
            API_USER_AGENT: "ua",
            "device": {"gw": "GW123", "plantName": "Boiler", "sn": "SN1"},
        },
        options={},
    )
    entry.add_to_hass(hass)
    return entry


async def test_options_flow_opens(hass: HomeAssistant, mock_entry: MockConfigEntry):
    """Options flow must open without error on current HA (issue #428)."""
    result = await hass.config_entries.options.async_init(mock_entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_save(hass: HomeAssistant, mock_entry: MockConfigEntry):
    """Submitting the options form must persist values."""
    result = await hass.config_entries.options.async_init(mock_entry.entry_id)

    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_SCAN_INTERVAL: 240,
            ENERGY_SCAN_INTERVAL: 30,
            BUS_ERRORS_SCAN_INTERVAL: 600,
        },
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert mock_entry.options[CONF_SCAN_INTERVAL] == 240
    assert mock_entry.options[ENERGY_SCAN_INTERVAL] == 30
    assert mock_entry.options[BUS_ERRORS_SCAN_INTERVAL] == 600
