#!/usr/bin/env python3
"""MiniMax Anthropic API Daemon - Runs on host with Anthropic SDK access."""

import argparse
import asyncio
import json
import logging
import signal
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

import anthropic

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
_LOGGER = logging.getLogger("minimax-daemon")

ANTHROPIC_API_URL = "https://api.minimax.io/anthropic/v1/messages"
DEFAULT_PORT = 8124


class AnthropicDaemon:
    """Manages Anthropic API calls."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = anthropic.Anthropic(
            base_url=ANTHROPIC_API_URL.rsplit("/v1", 1)[0],
            api_key=api_key,
        )
        _LOGGER.info("Anthropic client initialized")

    def chat(self, model: str, system_prompt: str, messages: list) -> dict:
        """Send chat request using Anthropic API."""
        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=1000,
                system=system_prompt,
                messages=messages,
            )

            content_blocks = response.content
            text_parts = []
            tool_calls = []

            for block in content_blocks:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append(
                        {
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        }
                    )

            return {
                "success": True,
                "text": "\n".join(text_parts) if text_parts else "",
                "tool_calls": tool_calls,
                "stop_reason": response.stop_reason,
            }

        except Exception as err:
            _LOGGER.error("Anthropic API error: %s", err)
            return {
                "success": False,
                "error": str(err),
            }


class DaemonHandler(BaseHTTPRequestHandler):
    """HTTP handler for daemon requests."""

    daemon_instance = None

    def log_message(self, format, *args):
        """Override to use our logger."""
        _LOGGER.debug(
            "%s - - [%s] %s"
            % (self.address_string(), self.log_date_time_string(), format % args)
        )

    def do_POST(self):
        """Handle POST requests."""
        if self.path != "/chat":
            self.send_error(404, "Not Found")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return

        model = data.get("model", "MiniMax-M2.7")
        system_prompt = data.get("system_prompt", "")
        messages = data.get("messages", [])

        _LOGGER.info("Chat request: model=%s, messages=%d", model, len(messages))

        result = self.daemon_instance.chat(model, system_prompt, messages)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode("utf-8"))

    def do_GET(self):
        """Handle GET requests - health check."""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
        else:
            self.send_error(404, "Not Found")


def run_daemon(api_key: str, port: int):
    """Run the daemon server."""
    daemon = AnthropicDaemon(api_key)
    DaemonHandler.daemon_instance = daemon

    server = HTTPServer(("0.0.0.0", port), DaemonHandler)
    _LOGGER.info("MiniMax daemon listening on port %d", port)

    def signal_handler(sig, frame):
        _LOGGER.info("Shutting down daemon...")
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MiniMax Anthropic API Daemon")
    parser.add_argument("--api-key", required=True, help="MiniMax API key")
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, help="Port to listen on"
    )
    args = parser.parse_args()

    run_daemon(args.api_key, args.port)
