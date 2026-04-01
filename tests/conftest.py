"""Pytest configuration for MiniMax integration tests."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture
def enable_custom_integrations(hass: HomeAssistant) -> None:
    """Enable custom integrations loading."""
    from custom_components.minimax.const import DOMAIN

    hass.data.setdefault(DOMAIN, {})


@pytest.fixture
def mock_server_response():
    """Configure mock server responses."""
    return {
        "/v1/text/chatcompletion_v2": {
            "id": "chatcmpl-123",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help you?",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"input_tokens": 10, "output_tokens": 20},
        },
        "/v1/audio/t2a_v2": {
            "id": "tts-123",
            "choices": [{"finish_reason": "stop", "index": 0}],
            "data": "Zmxha2VfYXVkaW9fZGF0YQ==",
        },
        "/v1/audio/transcription": {
            "text": "This is transcribed text.",
            "code": 0,
            "msg": "success",
        },
    }
