"""The MiniMax integration."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
)
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, RECOMMENDED_CHAT_MODEL

PLATFORMS = (
    Platform.CONVERSATION,
    Platform.STT,
    Platform.TTS,
)

_LOGGER = logging.getLogger(__name__)

type MiniMaxConfigEntry = ConfigEntry[dict[str, Any]]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up MiniMax integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MiniMaxConfigEntry) -> bool:
    """Set up MiniMax from a config entry."""
    _LOGGER.info("Setting up MiniMax integration")
    api_key = entry.data.get(CONF_API_KEY)
    _LOGGER.debug("API key present: %s", bool(api_key))

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            _LOGGER.debug("Validating API key with MiniMax API")
            response = await client.post(
                "https://api.minimax.io/v1/text/chatcompletion_v2",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": RECOMMENDED_CHAT_MODEL,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                },
            )
            _LOGGER.debug("API response status: %s", response.status_code)
            if response.status_code == 401:
                raise ConfigEntryAuthFailed("Invalid API key")
            if response.status_code != 200:
                raise ConfigEntryError(f"API error: {response.status_code}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            _LOGGER.error("Authentication failed: Invalid API key")
            raise ConfigEntryAuthFailed("Invalid API key") from e
        _LOGGER.error("HTTP error: %s", e.response.status_code)
        raise ConfigEntryError(f"HTTP error: {e.response.status_code}") from e
    except httpx.TimeoutException as e:
        _LOGGER.error("Timeout connecting to MiniMax API")
        raise ConfigEntryNotReady("Timeout connecting to MiniMax API") from e

    _LOGGER.info("MiniMax API connection successful")
    entry.runtime_data = {"api_key": api_key}
    _LOGGER.debug("Forwarding entry to platforms: %s", PLATFORMS)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.info("MiniMax integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MiniMaxConfigEntry) -> bool:
    """Unload MiniMax entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    return True
