"""Tests for MiniMax API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from custom_components.minimax.api import (
    MiniMaxApiClient,
    MiniMaxApiClientError,
)

TEST_API_KEY = "test_api_key_12345"
TEST_BASE_URL = "https://api.minimax.io"


@pytest.fixture
async def api_client():
    """Create an API client for testing."""
    return MiniMaxApiClient(api_key=TEST_API_KEY)


@pytest.fixture
async def mock_chat_response():
    """Mock chat completion response."""
    return {
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
    }


@pytest.fixture
async def mock_tts_response():
    """Mock TTS response."""
    return b"fake_audio_data"


@pytest.fixture
async def mock_stt_response():
    """Mock STT response."""
    return {
        "text": "This is transcribed text.",
        "code": 0,
        "msg": "success",
    }


class TestMiniMaxApiClientInit:
    """Test MiniMaxApiClient initialization."""

    def test_init(self, api_client: MiniMaxApiClient):
        """Test client initialization."""
        assert api_client.api_key == TEST_API_KEY
        assert api_client.base_url == TEST_BASE_URL


class TestAsyncChat:
    """Test async_chat method."""

    @pytest.mark.asyncio
    async def test_async_chat_success(
        self,
        api_client: MiniMaxApiClient,
        mock_chat_response: dict,
    ):
        """Test successful chat request."""
        app = web.Application()
        call_log = []

        async def handle_chat(request: web.Request) -> web.Response:
            call_log.append(await request.json())
            return web.json_response(mock_chat_response)

        app.router.add_post("/anthropic/v1/messages", handle_chat)

        async with TestClient(TestServer(app)) as client:
            with patch.object(api_client, "_client", client):
                result = await api_client.async_chat(
                    messages=[{"role": "user", "content": "Hi"}]
                )

        assert result["success"] is True
        assert result["text"] == "Hello! How can I help you?"
        assert call_log[0]["messages"] == [{"role": "user", "content": "Hi"}]

    @pytest.mark.asyncio
    async def test_async_chat_with_tools(
        self,
        api_client: MiniMaxApiClient,
        mock_chat_response: dict,
    ):
        """Test chat request with tools."""
        app = web.Application()
        call_log = []

        async def handle_chat(request: web.Request) -> web.Response:
            call_log.append(await request.json())
            return web.json_response(mock_chat_response)

        app.router.add_post("/anthropic/v1/messages", handle_chat)

        tools = [
            {
                "name": "get_weather",
                "description": "Get weather for a location",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"},
                    },
                },
            }
        ]

        async with TestClient(TestServer(app)) as client:
            with patch.object(api_client, "_client", client):
                result = await api_client.async_chat(
                    messages=[{"role": "user", "content": "What's the weather?"}],
                    tools=tools,
                )

        assert result["success"] is True
        assert "tools" in call_log[0]
        assert call_log[0]["tools"] == tools

    @pytest.mark.asyncio
    async def test_async_chat_http_error(self, api_client: MiniMaxApiClient):
        """Test chat request with HTTP error."""
        app = web.Application()

        async def handle_chat(request: web.Request) -> web.Response:
            return web.Response(status=401, text="Unauthorized")

        app.router.add_post("/anthropic/v1/messages", handle_chat)

        async with TestClient(TestServer(app)) as client:
            with patch.object(api_client, "_client", client):
                with pytest.raises(MiniMaxApiClientError):
                    await api_client.async_chat(
                        messages=[{"role": "user", "content": "Hi"}]
                    )

    @pytest.mark.asyncio
    async def test_async_chat_timeout(self, api_client: MiniMaxApiClient):
        """Test chat request with timeout."""
        app = web.Application()

        async def handle_chat(request: web.Request) -> web.Response:
            raise TimeoutError("Connection timed out")

        app.router.add_post("/anthropic/v1/messages", handle_chat)

        async with TestClient(TestServer(app)) as client:
            with patch.object(api_client, "_client", client):
                with pytest.raises(MiniMaxApiClientError):
                    await api_client.async_chat(
                        messages=[{"role": "user", "content": "Hi"}]
                    )


class TestAsyncTTS:
    """Test async_tts method."""

    @pytest.mark.asyncio
    async def test_async_tts_success(
        self,
        api_client: MiniMaxApiClient,
        mock_tts_response: bytes,
    ):
        """Test successful TTS request."""
        app = web.Application()
        call_log = []

        async def handle_tts(request: web.Request) -> web.Response:
            data = await request.post()
            call_log.append({"text": data.get("text"), "model": data.get("model")})
            return web.Response(body=mock_tts_response)

        app.router.add_post("/v1/audio/t2a_v2", handle_tts)

        async with TestClient(TestServer(app)) as client:
            with patch.object(api_client, "_client", client):
                result = await api_client.async_tts(
                    text="Hello world", voice_id="male-qn-qns"
                )

        assert result == mock_tts_response
        assert call_log[0]["text"] == "Hello world"

    @pytest.mark.asyncio
    async def test_async_tts_http_error(self, api_client: MiniMaxApiClient):
        """Test TTS request with HTTP error."""
        app = web.Application()

        async def handle_tts(request: web.Request) -> web.Response:
            return web.Response(status=500, text="Internal Server Error")

        app.router.add_post("/v1/audio/t2a_v2", handle_tts)

        async with TestClient(TestServer(app)) as client:
            with patch.object(api_client, "_client", client):
                with pytest.raises(MiniMaxApiClientError):
                    await api_client.async_tts(
                        text="Hello world", voice_id="male-qn-qns"
                    )


class TestAsyncSTT:
    """Test async_stt method."""

    @pytest.mark.asyncio
    async def test_async_stt_success(
        self,
        api_client: MiniMaxApiClient,
        mock_stt_response: dict,
    ):
        """Test successful STT request."""
        app = web.Application()
        call_log = []

        async def handle_stt(request: web.Request) -> web.Response:
            data = await request.post()
            call_log.append({"file": data.get("file"), "model": data.get("model")})
            return web.json_response(mock_stt_response)

        app.router.add_post("/v1/audio/transcription", handle_stt)

        audio_content = b"fake_audio_content"

        async with TestClient(TestServer(app)) as client:
            with patch.object(api_client, "_client", client):
                result = await api_client.async_stt(audio_content=audio_content)

        assert result == "This is transcribed text."
        assert call_log[0]["file"] == audio_content

    @pytest.mark.asyncio
    async def test_async_stt_http_error(self, api_client: MiniMaxApiClient):
        """Test STT request with HTTP error."""
        app = web.Application()

        async def handle_stt(request: web.Request) -> web.Response:
            return web.Response(status=500, text="Internal Server Error")

        app.router.add_post("/v1/audio/transcription", handle_stt)

        async with TestClient(TestServer(app)) as client:
            with patch.object(api_client, "_client", client):
                with pytest.raises(MiniMaxApiClientError):
                    await api_client.async_stt(audio_content=b"fake_audio")


class TestAsyncVerifyConnection:
    """Test async_verify_connection method."""

    @pytest.mark.asyncio
    async def test_verify_connection_success(self, api_client: MiniMaxApiClient):
        """Test successful connection verification."""
        app = web.Application()

        async def handle_messages(request: web.Request) -> web.Response:
            return web.json_response(
                {
                    "id": "verify-123",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "ok"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"input_tokens": 1, "output_tokens": 1},
                }
            )

        app.router.add_post("/anthropic/v1/messages", handle_messages)

        async with TestClient(TestServer(app)) as client:
            with patch.object(api_client, "_client", client):
                result = await api_client.async_verify_connection()

        assert result is True

    @pytest.mark.asyncio
    async def test_verify_connection_auth_failure(self, api_client: MiniMaxApiClient):
        """Test connection verification with auth failure."""
        app = web.Application()

        async def handle_messages(request: web.Request) -> web.Response:
            return web.Response(status=401, text="Unauthorized")

        app.router.add_post("/anthropic/v1/messages", handle_messages)

        async with TestClient(TestServer(app)) as client:
            with patch.object(api_client, "_client", client):
                with pytest.raises(MiniMaxApiClientError):
                    await api_client.async_verify_connection()

    @pytest.mark.asyncio
    async def test_verify_connection_rate_limit(self, api_client: MiniMaxApiClient):
        """Test connection verification with rate limit."""
        app = web.Application()

        async def handle_messages(request: web.Request) -> web.Response:
            return web.Response(status=429, text="Rate limit exceeded")

        app.router.add_post("/anthropic/v1/messages", handle_messages)

        async with TestClient(TestServer(app)) as client:
            with patch.object(api_client, "_client", client):
                with pytest.raises(MiniMaxApiClientError):
                    await api_client.async_verify_connection()
