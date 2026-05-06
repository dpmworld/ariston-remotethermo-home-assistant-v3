"""Tests for Ariston water heater entity."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant

from ariston.const import (
    NuosSplitOperativeMode,
    NuosSplitProperties,
    SystemType,
    WheType,
)
from ariston.nuos_split_device import AristonNuosSplitDevice

from custom_components.ariston.const import AristonWaterHeaterEntityDescription
from custom_components.ariston.water_heater import AristonWaterHeater


def make_nuos_device() -> AristonNuosSplitDevice:
    """Build a NuosSplit device without networking."""
    api = MagicMock()
    api.set_nuos_mode = MagicMock()
    api.async_set_nuos_mode = AsyncMock()
    api.set_nuos_temperature = MagicMock()
    api.async_set_nuos_temperature = AsyncMock()
    api.set_velis_power = MagicMock()
    api.async_set_velis_power = AsyncMock()

    device = AristonNuosSplitDevice.__new__(AristonNuosSplitDevice)
    device.api = api
    device.gw = "GW123"
    device.data = {
        NuosSplitProperties.WATER_TEMP: 46.0,
        NuosSplitProperties.COMFORT_TEMP: 50.0,
        NuosSplitProperties.REDUCED_TEMP: 45.0,
        NuosSplitProperties.OP_MODE: NuosSplitOperativeMode.GREEN.value,
        NuosSplitProperties.BOOST_ON: False,
        "on": True,
    }
    device.plant_settings = {}
    device.features = {}
    device.attributes = {"wheType": WheType.NuosSplit.value, "wheModelType": 5}
    return device


def make_entity(device, on_refresh=None) -> AristonWaterHeater:
    """Build a water heater entity with a fake coordinator + description.

    `on_refresh` (optional) is invoked when `coordinator.async_request_refresh`
    is awaited, so tests can simulate the cloud roundtrip rewriting
    `device.data` from the server response.
    """
    coordinator = MagicMock()
    coordinator.device = device
    coordinator.last_update_success = True

    async def _refresh():
        if on_refresh is not None:
            on_refresh()

    coordinator.async_request_refresh = AsyncMock(side_effect=_refresh)

    description = AristonWaterHeaterEntityDescription(
        key="ariston_water_heater",
        name="Ariston Water Heater",
        coordinator="coordinator",
        device_features=None,
        system_types=[SystemType.VELIS],
        whe_types=[WheType.NuosSplit],
    )

    entity = AristonWaterHeater(coordinator, description)
    entity.hass = MagicMock()
    entity.entity_id = "water_heater.ariston"
    entity.async_write_ha_state = MagicMock()
    return entity


async def test_set_operation_mode_requests_refresh():
    """Setter must trigger a coordinator refresh to bypass the lib cache desync (#461)."""
    device = make_nuos_device()

    # Simulate the cloud update writing the new mode into the right key on refresh.
    def fake_refresh():
        sent_value = device.api.async_set_nuos_mode.await_args.args[1].value
        device.data[NuosSplitProperties.OP_MODE] = sent_value

    entity = make_entity(device, on_refresh=fake_refresh)

    await entity.async_set_operation_mode("COMFORT")

    entity.coordinator.async_request_refresh.assert_awaited_once()
    assert entity.current_operation == "COMFORT"


async def test_set_operation_mode_all_options():
    """All NuosSplit modes round-trip through the setter and a coordinator refresh."""
    device = make_nuos_device()

    def fake_refresh():
        sent_value = device.api.async_set_nuos_mode.await_args.args[1].value
        device.data[NuosSplitProperties.OP_MODE] = sent_value

    entity = make_entity(device, on_refresh=fake_refresh)

    for mode in ("GREEN", "COMFORT", "FAST", "IMEMORY"):
        await entity.async_set_operation_mode(mode)
        assert entity.current_operation == mode, f"mode {mode} round-trip failed"


async def test_turn_off_writes_ha_state():
    """Turning off must refresh the HA entity state, otherwise the toggle stays stale."""
    device = make_nuos_device()
    entity = make_entity(device)

    await entity.async_turn_off()

    device.api.async_set_velis_power.assert_awaited_once()
    entity.async_write_ha_state.assert_called_once()
    assert device.data["on"] is False


async def test_turn_on_writes_ha_state():
    """Turning on must refresh the HA entity state."""
    device = make_nuos_device()
    device.data["on"] = False
    entity = make_entity(device)

    await entity.async_turn_on()

    device.api.async_set_velis_power.assert_awaited_once()
    entity.async_write_ha_state.assert_called_once()
    assert device.data["on"] is True
