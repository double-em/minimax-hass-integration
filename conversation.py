"""Conversation support for MiniMax using Anthropic API or Standard API."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

import httpx
from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_CHAT_MODEL,
    CONF_CONVERSATION_TTS_ENABLED,
    CONF_PROMPT,
    DOMAIN,
    LOGGER,
    RECOMMENDED_CHAT_MODEL,
    is_anthropic_model,
)

_LOGGER = logging.getLogger(__name__)

MINIMAX_STANDARD_API = "https://api.minimax.io/v1/text/chatcompletion_v2"
MINIMAX_DAEMON_URL = "http://localhost:8124/chat"
MAX_TOOL_CALLS = 10


def _get_exposed_entities(hass: HomeAssistant, assistant: str) -> dict[str, Any]:
    """Get exposed entities for the assistant."""
    from homeassistant.helpers import llm

    exposed_entities = llm._get_exposed_entities(hass, assistant)
    return exposed_entities


def _build_system_prompt(user_prompt: str, hass: HomeAssistant, agent_id: str) -> str:
    """Build system prompt with exposed entity state."""
    try:
        exposed = _get_exposed_entities(hass, agent_id)
        entities_info = ""

        if exposed and exposed.get("entities"):
            entities_info = (
                "\n\nStatic Context - Your Home Assistant devices and their states:\n"
            )
            for entity_data in exposed["entities"].values():
                entities_info += f"- {entity_data.get('name', entity_data.get('entity_id'))}: {entity_data.get('state', 'unknown')}\n"
        else:
            all_states = hass.states.async_all()
            if all_states:
                entities_info = "\n\nStatic Context - Your Home Assistant devices and their states:\n"
                for state in sorted(all_states, key=lambda s: s.entity_id):
                    if state.entity_id.startswith(
                        "automation."
                    ) or state.entity_id.startswith("scene."):
                        continue
                    entities_info += f"- {state.name}: {state.state}\n"

        return f"{user_prompt}{entities_info}"
    except Exception as err:
        LOGGER.warning("Could not get exposed entities: %s", err)
        return user_prompt


def _get_homeassistant_tools(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Get Home Assistant services as tools for MiniMax."""
    tools = []

    key_domains = [
        "homeassistant",
        "light",
        "switch",
        "climate",
        "fan",
        "cover",
        "lock",
        "alarm_control_panel",
        "media_player",
        "input_boolean",
        "automation",
        "script",
    ]

    try:
        descriptions = hass.services.async_get_all_descriptions()
    except Exception as err:
        LOGGER.warning("Could not get service descriptions: %s", err)
        return tools

    for domain, services in descriptions.items():
        if domain not in key_domains:
            continue

        for service_name, service_desc in services.items():
            if service_name.startswith("_"):
                continue

            tool_name = f"{domain}.{service_name}"
            description = service_desc.get(
                "name", service_desc.get("description", f"{domain} {service_name}")
            )

            properties = {}
            required = []
            fields = service_desc.get("fields", {})

            for field_name, field_desc in fields.items():
                field_type = "string"
                if field_desc.get("schema"):
                    field_type = "string"
                elif field_desc.get("example"):
                    field_type = type(field_desc["example"]).__name__

                properties[field_name] = {
                    "type": field_type,
                    "description": field_desc.get("description", field_name),
                }
                if field_desc.get("required"):
                    required.append(field_name)

            if "entity_id" not in properties:
                properties["entity_id"] = {
                    "type": "string",
                    "description": "The entity ID to target (e.g., light.living_room)",
                }

            tool = {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                    },
                },
            }

            if required:
                tool["function"]["parameters"]["required"] = required

            tools.append(tool)

    LOGGER.debug("Generated %d Home Assistant tools", len(tools))
    return tools


async def _call_service(
    hass: HomeAssistant, domain: str, service: str, data: dict[str, Any]
) -> dict[str, Any]:
    """Call a Home Assistant service."""
    try:
        result = await hass.services.async_call(
            domain,
            service,
            data,
            blocking=True,
            return_response=True,
        )
        LOGGER.debug("Service call %s.%s result: %s", domain, service, result)
        return {"success": True, "result": result}
    except Exception as err:
        LOGGER.error("Service call failed: %s", err)
        return {"success": False, "error": str(err)}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up conversation entities."""
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type != "conversation":
            continue

        async_add_entities(
            [MiniMaxConversationEntity(config_entry, subentry)],
            config_subentry_id=subentry.subentry_id,
        )


class MiniMaxConversationEntity(
    conversation.ConversationEntity,
    conversation.AbstractConversationAgent,
):
    """MiniMax conversation agent."""

    _attr_supported_features = conversation.ConversationEntityFeature.CONTROL

    def __init__(self, entry: ConfigEntry, subentry: ConfigSubentry) -> None:
        """Initialize the agent."""
        self.entry = entry
        self.subentry = subentry
        self._attr_name = subentry.title
        self._attr_unique_id = subentry.subentry_id
        self._tts_enabled = subentry.data.get(CONF_CONVERSATION_TTS_ENABLED, True)
        self._tools: list[dict[str, Any]] | None = None

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return a list of supported languages."""
        return MATCH_ALL

    def _get_api_key(self) -> str:
        """Get API key from config entry."""
        return self.entry.runtime_data.get("api_key", "")

    async def async_added_to_hass(self) -> None:
        """When entity is added to Home Assistant."""
        _LOGGER.debug("Conversation entity added to hass, setting agent")
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)
        _LOGGER.info("MiniMax conversation agent registered: %s", self._attr_unique_id)

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from Home Assistant."""
        _LOGGER.debug("Conversation entity removing from hass")
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    def _get_tools(self) -> list[dict[str, Any]]:
        """Get or cache tools."""
        if self._tools is None:
            self._tools = _get_homeassistant_tools(self.hass)
        return self._tools

    async def _execute_tool_calls(
        self, tool_calls: list[dict[str, Any]], messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Execute tool calls and return results."""
        results = []

        for tool_call in tool_calls[:MAX_TOOL_CALLS]:
            name = tool_call.get("name", "")
            args = tool_call.get("input", {})

            if not name:
                continue

            if "." in name:
                domain, service = name.split(".", 1)
            else:
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_call.get("id", ""),
                        "content": f"Invalid tool name: {name}",
                    }
                )
                continue

            _LOGGER.debug("Executing tool call: %s with args: %s", name, args)
            result = await _call_service(self.hass, domain, service, args)

            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_call.get("id", ""),
                    "content": str(result),
                }
            )

        return results

    async def _chat_anthropic(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Send chat request to local Anthropic daemon."""

        def _call_daemon() -> dict[str, Any]:
            """Call local daemon via HTTP."""
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    MINIMAX_DAEMON_URL,
                    json={
                        "model": model,
                        "system_prompt": system_prompt,
                        "messages": messages,
                        "tools": tools,
                    },
                )
                response.raise_for_status()
                return response.json()

        try:
            result = await self.hass.async_add_executor_job(_call_daemon)
            _LOGGER.debug("Daemon response: %s", result)

            if not result.get("success", False):
                error = result.get("error", "Unknown error")
                raise Exception(f"Daemon error: {error}")

            content_blocks = result.get("content", [])
            has_tool_use = result.get("tool_calls", [])

            if has_tool_use:
                tool_calls = []
                text_parts = []

                for block in content_blocks:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))

                for tc in result.get("tool_calls", []):
                    tool_calls.append(
                        {
                            "id": tc.get("id", ""),
                            "name": tc.get("name", ""),
                            "input": tc.get("input", {}),
                        }
                    )

                if tool_calls:
                    _LOGGER.debug("Tool calls returned: %d", len(tool_calls))
                    tool_results = await self._execute_tool_calls(tool_calls, messages)

                    messages.append(
                        {
                            "role": "assistant",
                            "content": content_blocks,
                        }
                    )

                    for result_item in tool_results:
                        messages.append({"role": "user", "content": [result_item]})

                    return await self._chat_anthropic(
                        system_prompt, messages, tools, model
                    )

                text = "\n".join(text_parts) if text_parts else ""
                return text, messages
            else:
                text = result.get("text", "")
                return text, messages

        except Exception as err:
            _LOGGER.error("Anthropic daemon error: %s", err)
            raise

    async def _chat_standard(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        model: str,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Send chat request using Standard OpenAI-compatible API (M2-her)."""
        api_key = self.entry.runtime_data.get("api_key", "")

        formatted_messages = []
        formatted_messages.append(
            {
                "role": "system",
                "name": "AI Assistant",
                "content": system_prompt,
            }
        )
        for msg in messages:
            formatted_messages.append(msg)

        def _call_api() -> dict[str, Any]:
            """Call API in thread to avoid blocking."""
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    MINIMAX_STANDARD_API,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": formatted_messages,
                        "temperature": 1.0,
                        "top_p": 0.95,
                        "max_completion_tokens": 2048,
                    },
                )
                response.raise_for_status()
                return response.json()

        try:
            result = await self.hass.async_add_executor_job(_call_api)
            _LOGGER.debug("Standard API response keys: %s", list(result.keys()))

            assistant_message = result["choices"][0]["message"]
            return assistant_message.get("content", ""), [assistant_message]

        except Exception as err:
            _LOGGER.error("Standard API error: %s", err)
            raise

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a conversation message."""
        _LOGGER.debug("Processing conversation input: %s", user_input.text)
        user_prompt = self.subentry.data.get(
            CONF_PROMPT,
            "You are EVA, a friendly AI home assistant. Be helpful and concise.",
        )
        system_prompt = _build_system_prompt(user_prompt, self.hass, DOMAIN)
        model = self.subentry.data.get(CONF_CHAT_MODEL, RECOMMENDED_CHAT_MODEL)

        use_anthropic = is_anthropic_model(model)

        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": user_input.text}]
                if use_anthropic
                else user_input.text,
            }
        ]

        if use_anthropic:
            tools = self._get_tools()
            _LOGGER.debug(
                "Using Anthropic API with model: %s, tools: %d", model, len(tools)
            )
            try:
                response_text, _ = await self._chat_anthropic(
                    system_prompt, messages, tools, model
                )
            except Exception as err:
                _LOGGER.error("Conversation error: %s", err)
                response_text = "Beklager, der opstod en fejl."
        else:
            _LOGGER.debug("Using Standard API with model: %s (no tools)", model)
            try:
                response_text, _ = await self._chat_standard(
                    system_prompt, messages, model
                )
            except Exception as err:
                _LOGGER.error("Conversation error: %s", err)
                response_text = "Beklager, der opstod en fejl."

        response_text = re.sub(
            re.compile(r"<think>.*?</think>", re.DOTALL),
            "",
            response_text,
        )
        response_text = response_text.strip()

        if not response_text:
            response_text = "Beklager, jeg kunne ikke få svar."

        intent_response = intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(response_text)

        return conversation.ConversationResult(
            response=intent_response,
            conversation_id=user_input.conversation_id,
        )
