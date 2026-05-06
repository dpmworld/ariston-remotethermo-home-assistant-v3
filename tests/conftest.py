"""Test config for Ariston integration."""

from pytest_homeassistant_custom_component.common import (  # noqa: F401
    MockConfigEntry,
)
import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom_components in HA tests."""
    yield
