"""Tests for unmatched RF status auto-bind."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.schellenberg_usb.api import SchellenbergUsbApi
from custom_components.schellenberg_usb.const import (
    CONF_COMMAND_DEVICE_ID,
    CONF_COMMAND_ENUM,
    CONF_STATUS_DEVICE_ID,
    CONF_STATUS_ENUM,
    CONF_STATUS_IDENTITY_SOURCE,
    STATUS_IDENTITY_SOURCE_REMOTE_DISCOVERY,
    STATUS_IDENTITY_SOURCE_UNKNOWN,
    SUBENTRY_TYPE_BLIND,
)


@pytest.mark.asyncio
async def test_auto_bind_status_identity_for_single_unknown_blind(
    hass: HomeAssistant,
) -> None:
    """Test one unknown-status blind adopts an unmatched RF identity."""
    api = SchellenbergUsbApi(hass, "/dev/ttyUSB0")
    api.config_entry_id = "entry-1"
    api.register_entity(
        None,
        None,
        "Terrace window",
        command_device_id="103E7C",
        command_enum="10",
    )

    subentry = SimpleNamespace(
        subentry_type=SUBENTRY_TYPE_BLIND,
        title="Terrace window",
        data={
            CONF_COMMAND_DEVICE_ID: "103E7C",
            CONF_COMMAND_ENUM: "10",
            CONF_STATUS_IDENTITY_SOURCE: STATUS_IDENTITY_SOURCE_UNKNOWN,
        },
    )
    entry = SimpleNamespace(subentries={"blind-1": subentry})
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=entry)
    hass.config_entries.async_update_subentry = MagicMock()

    with patch(
        "custom_components.schellenberg_usb.api.async_dispatcher_send"
    ) as mock_send:
        await api._async_try_auto_bind_status_identity("F4442C", "0E", "1F")

    assert ("F4442C", "0E") in api._registered_entity_keys
    hass.config_entries.async_update_subentry.assert_called_once()
    _entry, _sub, kwargs = (
        hass.config_entries.async_update_subentry.call_args.args[0],
        hass.config_entries.async_update_subentry.call_args.args[1],
        hass.config_entries.async_update_subentry.call_args.kwargs,
    )
    assert kwargs["data"][CONF_STATUS_DEVICE_ID] == "F4442C"
    assert kwargs["data"][CONF_STATUS_ENUM] == "0E"
    assert (
        kwargs["data"][CONF_STATUS_IDENTITY_SOURCE]
        == STATUS_IDENTITY_SOURCE_REMOTE_DISCOVERY
    )
    mock_send.assert_called_once()
    assert mock_send.call_args.args[1] == "schellenberg_usb_device_event_F4442C_0E"
    assert mock_send.call_args.args[2] == "1F"


@pytest.mark.asyncio
async def test_auto_bind_skipped_when_multiple_unknown_blinds(
    hass: HomeAssistant,
) -> None:
    """Test auto-bind refuses to guess when more than one blind lacks status."""
    api = SchellenbergUsbApi(hass, "/dev/ttyUSB0")
    api.config_entry_id = "entry-1"

    blinds = {
        "a": SimpleNamespace(
            subentry_type=SUBENTRY_TYPE_BLIND,
            title="A",
            data={CONF_STATUS_IDENTITY_SOURCE: STATUS_IDENTITY_SOURCE_UNKNOWN},
        ),
        "b": SimpleNamespace(
            subentry_type=SUBENTRY_TYPE_BLIND,
            title="B",
            data={CONF_STATUS_IDENTITY_SOURCE: STATUS_IDENTITY_SOURCE_UNKNOWN},
        ),
    }
    entry = SimpleNamespace(subentries=blinds)
    hass.config_entries = MagicMock()
    hass.config_entries.async_get_entry = MagicMock(return_value=entry)
    hass.config_entries.async_update_subentry = MagicMock()

    await api._async_try_auto_bind_status_identity("F4442C", "0E", "1F")

    hass.config_entries.async_update_subentry.assert_not_called()
    assert ("F4442C", "0E") not in api._registered_entity_keys
