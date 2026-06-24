#!/usr/bin/env bash
# One-shot installer — run this ONCE on the VM after rsync'ing the project there.
# It builds the venv, installs the server deps, and registers + starts the bot as
# a systemd service (auto-start on boot, auto-restart on crash).
set -euo pipefail
cd "$(dirname "$0")/.."          # project root

sudo apt-get update -y
sudo apt-get install -y python3-venv python3-dev build-essential

python3 -m venv venv
venv/bin/pip install -U pip
venv/bin/pip install -r deploy/requirements-server.txt

# Install + start the service.
sudo cp deploy/stock-bot.service /etc/systemd/system/stock-bot.service
sudo systemctl daemon-reload
sudo systemctl enable --now stock-bot

echo
echo "Done. The bot is now running and will survive reboots/crashes."
echo "  status: sudo systemctl status stock-bot"
echo "  logs:   journalctl -u stock-bot -f"
