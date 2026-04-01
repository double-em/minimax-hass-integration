"""Speech to text support for MiniMax."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterable

import httpx
from homeassistant.components import stt
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_CHAT_MODEL,
    CONF_PROMPT,
    RECOMMENDED_CHAT_MODEL,
)

_LOGGER = logging.getLogger(__name__)

MINIMAX_STT_API = "https://api.minimax.io/v1/audio/transcription"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up STT entities."""
    _LOGGER.debug("Setting up STT entities")
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type != "stt":
            continue
        _LOGGER.debug("Adding STT entity: %s", subentry.subentry_id)

        async_add_entities(
            [MiniMaxSTTEntity(config_entry, subentry)],
            config_subentry_id=subentry.subentry_id,
        )


class MiniMaxSTTEntity(stt.SpeechToTextEntity):
    """MiniMax speech-to-text entity."""

    _attr_supported_languages = ["en-US", "zh-CN"]

    def __init__(self, config_entry: ConfigEntry, subentry: ConfigSubentry) -> None:
        """Initialize the STT entity."""
        self.entry = config_entry
        self.subentry = subentry
        self._attr_name = subentry.title
        self._attr_unique_id = subentry.subentry_id

    @property
    def supported_languages(self) -> list[str]:
        """Return a list of supported languages."""
        return self._attr_supported_languages

    @property
    def supported_formats(self) -> list[stt.AudioFormats]:
        """Return a list of supported formats."""
        return [stt.AudioFormats.WAV, stt.AudioFormats.OGG, stt.AudioFormats.MP3]

    @property
    def supported_codecs(self) -> list[stt.AudioCodecs]:
        """Return a list of supported codecs."""
        return [stt.AudioCodecs.PCM, stt.AudioCodecs.OPUS]

    @property
    def supported_bit_rates(self) -> list[stt.AudioBitRates]:
        """Return a list of supported bit rates."""
        return [stt.AudioBitRates.BITRATE_16, stt.AudioBitRates.BITRATE_32]

    @property
    def supported_sample_rates(self) -> list[stt.AudioSampleRates]:
        """Return a list of supported sample rates."""
        return [
            stt.AudioSampleRates.SAMPLERATE_16000,
            stt.AudioSampleRates.SAMPLERATE_32000,
        ]

    @property
    def supported_channels(self) -> list[stt.AudioChannels]:
        """Return a list of supported channels."""
        return [stt.AudioChannels.CHANNEL_MONO]

    async def async_process_audio_stream(
        self, metadata: stt.SpeechMetadata, stream: AsyncIterable[bytes]
    ) -> stt.SpeechResult:
        """Process an audio stream to STT service."""
        _LOGGER.debug("Processing STT audio stream, language: %s", metadata.language)
        api_key = self.entry.runtime_data.get("api_key", "")
        prompt = self.subentry.data.get(CONF_PROMPT, "Transcribe the audio")
        model = self.subentry.data.get(CONF_CHAT_MODEL, RECOMMENDED_CHAT_MODEL)

        audio_data = b""
        async for chunk in stream:
            audio_data += chunk
        _LOGGER.debug("Received %d bytes of audio data", len(audio_data))

        try:
            _LOGGER.debug("Calling STT API with model: %s", model)
            async with httpx.AsyncClient(timeout=60.0) as client:
                files = {
                    "file": ("audio.wav", audio_data, f"audio/{metadata.format.value}"),
                    "model": (None, model),
                    "language": (None, metadata.language),
                    "prompt": (None, prompt),
                }

                response = await client.post(
                    MINIMAX_STT_API,
                    headers={"Authorization": f"Bearer {api_key}"},
                    files=files,
                )
                response.raise_for_status()
                result = response.json()

                text = result.get("text", "")
                _LOGGER.debug("STT result: %s", text)
                if text:
                    return stt.SpeechResult(text, stt.SpeechResultState.SUCCESS)

                _LOGGER.warning("STT returned empty text")
                return stt.SpeechResult(None, stt.SpeechResultState.ERROR)

        except Exception as err:
            _LOGGER.error("Error during STT: %s", err)
            return stt.SpeechResult(None, stt.SpeechResultState.ERROR)
