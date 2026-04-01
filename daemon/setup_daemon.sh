#!/bin/bash
# Setup script for MiniMax Anthropic Daemon

set -e

DAEMON_DIR="/homeassistant/minimax-daemon"
DAEMON_SCRIPT="$DAEMON_DIR/minimax_daemon.py"
SERVICE_FILE="/etc/systemd/system/minimax-daemon.service"

# Get API key from HA config or environment
if [ -z "$MINIMAX_API_KEY" ]; then
    # Try to get from HA secrets or config
    API_KEY=$(grep -oP '(?<=api_key:\s)[\w-]+' /homeassistant/secrets.yaml 2>/dev/null || echo "")
    if [ -z "$API_KEY" ]; then
        echo "Error: MINIMAX_API_KEY not set and could not find in secrets.yaml"
        echo "Set MINIMAX_API_KEY environment variable or add api_key to /homeassistant/secrets.yaml"
        exit 1
    fi
else
    API_KEY="$MINIMAX_API_KEY"
fi

# Create daemon directory
mkdir -p "$DAEMON_DIR"

# Copy daemon script
cp /homeassistant/minimax_daemon.py "$DAEMON_SCRIPT"

# Update service file with API key
sed "s|YOUR_API_KEY|$API_KEY|g" /homeassistant/minimax-daemon.service.tmpl > "$SERVICE_FILE"

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable minimax-daemon
systemctl restart minimax-daemon

echo "MiniMax daemon installed and started"
systemctl status minimax-daemon --no-pager
