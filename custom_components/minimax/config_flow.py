"""Config flow for MiniMax integration."""

from __future__ import annotations

import logging
from typing import Any
import voluptuous as vol

_LOGGER = logging.getLogger(__name__)

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TemplateSelector,
)

from .api import MiniMaxApiClient, MiniMaxApiClientError
from .const import (
    CONF_API_KEY,
    CONF_CHAT_MODEL,
    CONF_CONVERSATION_EXPIRY_MINUTES,
    CONF_CONVERSATION_MAX_TOKENS,
    CONF_CONVERSATION_TTS_ENABLED,
    CONF_PITCH,
    CONF_PROMPT,
    CONF_RECOMMENDED,
    CONF_SPEED,
    CONF_VOICE_ID,
    CONF_VOL,
    DEFAULT_CONVERSATION_EXPIRY_MINUTES,
    DEFAULT_CONVERSATION_MAX_TOKENS,
    DEFAULT_CONVERSATION_NAME,
    DEFAULT_CONVERSATION_TTS_ENABLED,
    DEFAULT_PITCH,
    DEFAULT_SPEED,
    DEFAULT_TITLE,
    DEFAULT_VOL,
    DOMAIN,
    CHAT_MODELS,
    RECOMMENDED_CHAT_MODEL,
    RECOMMENDED_CONVERSATION_OPTIONS,
    RECOMMENDED_STT_OPTIONS,
    RECOMMENDED_TTS_OPTIONS,
    VOICE_IDS,
)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
    }
)


class InvalidAuthError(Exception):
    pass


class CannotConnectError(Exception):
    pass


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the user input allows us to connect."""
    _LOGGER.debug("Validating API key")
    api_key = data[CONF_API_KEY]

    client = MiniMaxApiClient(
        api_key=api_key,
        session=async_get_clientsession(hass),
    )

    if not await client.async_verify_connection():
        raise CannotConnectError("Failed to connect to MiniMax API")


class MiniMaxConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MiniMax."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        _LOGGER.debug("async_step_user called with input: %s", user_input)
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match(user_input)
            try:
                await validate_input(self.hass, user_input)
            except InvalidAuthError:
                _LOGGER.warning("Invalid auth during config flow")
                errors["base"] = "invalid_auth"
            except CannotConnectError as e:
                _LOGGER.warning("Cannot connect during config flow: %s", e)
                errors["base"] = "cannot_connect"
            except MiniMaxApiClientError as e:
                err_str = str(e).lower()
                if "invalid api key" in err_str or "401" in err_str:
                    _LOGGER.warning("Invalid auth during config flow: %s", e)
                    errors["base"] = "invalid_auth"
                else:
                    _LOGGER.warning("Cannot connect during config flow: %s", e)
                    errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.error("Unknown error during config flow: %s", e)
                errors["base"] = "unknown"
            else:
                _LOGGER.info("Config flow validation successful, creating entry")
                if self.source == SOURCE_REAUTH:
                    _LOGGER.debug("Re-auth flow, updating entry")
                    return self.async_update_reload_and_abort(
                        self._get_reauth_entry(),
                        data=user_input,
                    )
                return self.async_create_entry(
                    title=DEFAULT_TITLE,
                    data=user_input,
                    subentries=[
                        {
                            "subentry_type": "conversation",
                            "data": RECOMMENDED_CONVERSATION_OPTIONS,
                            "title": DEFAULT_CONVERSATION_NAME,
                            "unique_id": None,
                        },
                        {
                            "subentry_type": "tts",
                            "data": RECOMMENDED_TTS_OPTIONS,
                            "title": "MiniMax TTS",
                            "unique_id": None,
                        },
                        {
                            "subentry_type": "stt",
                            "data": RECOMMENDED_STT_OPTIONS,
                            "title": "MiniMax STT",
                            "unique_id": None,
                        },
                    ],
                )
        _LOGGER.debug("Showing user form")
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle re-authentication."""
        return await self.async_step_user()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this integration."""
        return {
            "conversation": LLMSubentryFlowHandler,
            "tts": LLMSubentryFlowHandler,
            "stt": LLMSubentryFlowHandler,
        }


class LLMSubentryFlowHandler(ConfigSubentryFlow):
    """Flow for managing subentries."""

    last_rendered_recommended = False

    @property
    def _is_new(self) -> bool:
        """Return if this is a new subentry."""
        return self.source == "user"

    async def async_step_set_options(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Set subentry options."""
        _LOGGER.debug(
            "async_step_set_options called for %s, input: %s",
            self._subentry_type,
            user_input,
        )
        errors: dict[str, str] = {}

        if user_input is None:
            if self._is_new:
                options: dict[str, Any]
                if self._subentry_type == "tts":
                    options = RECOMMENDED_TTS_OPTIONS.copy()
                elif self._subentry_type == "stt":
                    options = RECOMMENDED_STT_OPTIONS.copy()
                else:
                    options = RECOMMENDED_CONVERSATION_OPTIONS.copy()
                _LOGGER.debug("New subentry, using recommended options: %s", options)
            else:
                options = self._get_reconfigure_subentry().data.copy()
                _LOGGER.debug("Existing subentry, current options: %s", options)
            self.last_rendered_recommended = bool(options.get(CONF_RECOMMENDED, False))
        else:
            _LOGGER.debug("User provided input: %s", user_input)
            if user_input.get(CONF_RECOMMENDED) == self.last_rendered_recommended:
                if self._is_new:
                    _LOGGER.info("Creating new subentry: %s", self._subentry_type)
                    return self.async_create_entry(
                        title=user_input.pop("name"),
                        data=user_input,
                    )
                _LOGGER.info("Updating existing subentry: %s", self._subentry_type)
                return self.async_update_and_abort(
                    self._get_entry(),
                    self._get_reconfigure_subentry(),
                    data=user_input,
                )
            self.last_rendered_recommended = user_input.get(CONF_RECOMMENDED, False)
            options = user_input

        schema = async_minimax_option_schema(self._is_new, self._subentry_type, options)
        _LOGGER.debug("Showing form for subentry type: %s", self._subentry_type)
        return self.async_show_form(
            step_id="set_options", data_schema=vol.Schema(schema), errors=errors
        )

    async_step_reconfigure = async_step_set_options
    async_step_user = async_step_set_options


def async_minimax_option_schema(
    is_new: bool,
    subentry_type: str,
    options: dict[str, Any],
) -> dict:
    """Return a schema for MiniMax options."""
    schema: dict[vol.Required | vol.Optional, Any] = {}

    if is_new:
        default_name = options.get("name")
        if not default_name:
            if subentry_type == "tts":
                default_name = "MiniMax TTS"
            elif subentry_type == "stt":
                default_name = "MiniMax STT"
            else:
                default_name = DEFAULT_CONVERSATION_NAME
        schema[vol.Required("name", default=default_name)] = str

    if subentry_type == "conversation":
        default_model = options.get(CONF_CHAT_MODEL, RECOMMENDED_CHAT_MODEL)
        schema.update(
            {
                vol.Optional(
                    CONF_CHAT_MODEL,
                    description={"suggested_value": default_model},
                ): SelectSelector(
                    SelectSelectorConfig(
                        mode=SelectSelectorMode.DROPDOWN,
                        options=CHAT_MODELS,
                    )
                ),
                vol.Optional(
                    CONF_PROMPT,
                    description={"suggested_value": options.get(CONF_PROMPT, "")},
                ): TemplateSelector(),
                vol.Optional(
                    CONF_CONVERSATION_TTS_ENABLED,
                    default=options.get(
                        CONF_CONVERSATION_TTS_ENABLED, DEFAULT_CONVERSATION_TTS_ENABLED
                    ),
                ): BooleanSelector(),
                vol.Optional(
                    CONF_CONVERSATION_MAX_TOKENS,
                    default=options.get(
                        CONF_CONVERSATION_MAX_TOKENS, DEFAULT_CONVERSATION_MAX_TOKENS
                    ),
                ): NumberSelector(NumberSelectorConfig(min=1000, max=32000, step=1000)),
                vol.Optional(
                    CONF_CONVERSATION_EXPIRY_MINUTES,
                    default=options.get(
                        CONF_CONVERSATION_EXPIRY_MINUTES,
                        DEFAULT_CONVERSATION_EXPIRY_MINUTES,
                    ),
                ): SelectSelector(
                    SelectSelectorConfig(
                        mode=SelectSelectorMode.DROPDOWN,
                        options=[
                            {"label": "5 minutes", "value": 5},
                            {"label": "15 minutes", "value": 15},
                            {"label": "30 minutes", "value": 30},
                            {"label": "1 hour", "value": 60},
                        ],
                    )
                ),
            }
        )
    elif subentry_type == "tts":
        default_voice = options.get(CONF_VOICE_ID, "English_PlayfulGirl")

        voice_options = []
        for voice_id in VOICE_IDS.get("en-US", []):
            voice_name = voice_id.split("_", 2)[-1].replace("_", " ").replace("-", " ")
            voice_options.append(
                {"label": f"English - {voice_name}", "value": voice_id}
            )

        schema.update(
            {
                vol.Optional(
                    CONF_VOICE_ID,
                    description={"suggested_value": default_voice},
                ): SelectSelector(
                    SelectSelectorConfig(
                        mode=SelectSelectorMode.DROPDOWN,
                        options=voice_options,
                    )
                ),
                vol.Optional(
                    CONF_SPEED,
                    default=options.get(CONF_SPEED, DEFAULT_SPEED),
                ): NumberSelector(NumberSelectorConfig(min=0.5, max=2.0, step=0.1)),
                vol.Optional(
                    CONF_VOL,
                    default=options.get(CONF_VOL, DEFAULT_VOL),
                ): NumberSelector(NumberSelectorConfig(min=0.0, max=2.0, step=0.1)),
                vol.Optional(
                    CONF_PITCH,
                    default=options.get(CONF_PITCH, DEFAULT_PITCH),
                ): NumberSelector(NumberSelectorConfig(min=-10, max=10, step=1)),
            }
        )
    elif subentry_type == "stt":
        schema.update(
            {
                vol.Optional(
                    CONF_PROMPT,
                    description={"suggested_value": options.get(CONF_PROMPT, "")},
                ): TemplateSelector(),
            }
        )

    schema[
        vol.Required(CONF_RECOMMENDED, default=options.get(CONF_RECOMMENDED, False))
    ] = bool

    return schema
