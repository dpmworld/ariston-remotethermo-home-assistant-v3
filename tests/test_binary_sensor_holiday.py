"""Tests for the Nuos holiday binary sensor and create_vacation service."""

import datetime as dt
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from ariston.const import NuosSplitProperties

from custom_components.ariston.const import (
    ARISTON_BINARY_SENSOR_TYPES,
    AristonBinarySensorEntityDescription,
)


def _holiday_description() -> AristonBinarySensorEntityDescription:
    for desc in ARISTON_BINARY_SENSOR_TYPES:
        if desc.key == NuosSplitProperties.HOLIDAY_UNTIL:
            return desc
    raise AssertionError("Nuos holiday binary sensor description missing")


def test_holiday_description_exposes_runtime_filter():
    desc = _holiday_description()
    assert desc.runtime_filter is not None


def test_holiday_runtime_filter_passes_when_key_present_with_value():
    desc = _holiday_description()
    device = SimpleNamespace(
        data={NuosSplitProperties.HOLIDAY_UNTIL: "2026-08-15T00:00:00"}
    )
    assert desc.runtime_filter(device) is True


def test_holiday_runtime_filter_passes_when_key_present_with_null():
    """Cloud may return holidayUntil: null when no holiday is scheduled but the device supports the endpoint."""
    desc = _holiday_description()
    device = SimpleNamespace(data={NuosSplitProperties.HOLIDAY_UNTIL: None})
    assert desc.runtime_filter(device) is True


def test_holiday_runtime_filter_skips_when_key_absent():
    desc = _holiday_description()
    device = SimpleNamespace(data={"otherKey": 1})
    assert desc.runtime_filter(device) is False


def test_holiday_runtime_filter_skips_when_data_missing():
    desc = _holiday_description()
    device = SimpleNamespace()
    assert desc.runtime_filter(device) is False


def test_holiday_get_is_on_uses_holiday_active():
    desc = _holiday_description()
    entity = SimpleNamespace(device=SimpleNamespace(holiday_active=True))
    assert desc.get_is_on(entity) is True
    entity.device = SimpleNamespace(holiday_active=False)
    assert desc.get_is_on(entity) is False


def test_holiday_extra_state_returns_end_date():
    desc = _holiday_description()
    assert desc.extra_states is not None
    method = desc.extra_states[0]["DeviceMethod"]
    entity = SimpleNamespace(
        device=SimpleNamespace(holiday_end_date="2026-08-15T00:00:00")
    )
    assert method(entity) == "2026-08-15T00:00:00"
