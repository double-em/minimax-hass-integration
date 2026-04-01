"""Tests for the MiniMax integration."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import web
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.minimax.const import DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

TEST_API_KEY = "test_api_key_12345"
TEST_CONFIG_ENTRY_ID = "minimax_test_entry_001"


def create_mock_minimax_client() -> AsyncMock:
    """Create mock MiniMax API client."""
    mock_client = AsyncMock()
    mock_client.async_verify_connection = AsyncMock(return_value=True)
    mock_client.async_chat = AsyncMock(
        return_value={
            "success": True,
            "text": "Hello! How can I help you?",
            "tool_calls": [],
            "stop_reason": "end_turn",
        }
    )
    mock_client.async_tts = AsyncMock(return_value=b"fake_audio_data")
    mock_client.async_stt = AsyncMock(return_value="This is transcribed text.")
    return mock_client


def create_mock_minimax_config_entry(
    hass: HomeAssistant,
    data: dict[str, Any] | None = None,
    entry_id: str | None = TEST_CONFIG_ENTRY_ID,
) -> MockConfigEntry:
    """Create a mock MiniMax config entry."""
    config_entry: MockConfigEntry = MockConfigEntry(
        entry_id=entry_id,
        domain=DOMAIN,
        data=data or {CONF_API_KEY: TEST_API_KEY},
        title="MiniMax",
        version=1,
        minor_version=1,
    )
    config_entry.add_to_hass(hass)
    return config_entry


async def setup_mock_minimax_config_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry | None = None,
    client: AsyncMock | None = None,
) -> ConfigEntry:
    """Add a mock MiniMax config entry to hass."""
    from custom_components.minimax import MiniMaxApiClient

    config_entry = config_entry or create_mock_minimax_config_entry(hass)
    client = client or create_mock_minimax_client()

    mock_runtime_data = client if isinstance(client, MiniMaxApiClient) else client

    with (
        patch(
            "custom_components.minimax.MiniMaxApiClient",
            return_value=client,
        ),
    ):
        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    return config_entry
