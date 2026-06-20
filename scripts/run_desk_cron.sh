#!/usr/bin/env bash
# Cron wrapper for the research desk. Activates the venv, runs the desk for the
# configured tickers, and appends output to a dated log. Telegram delivery is on
# unless you add --no-send.
#
# Install (run the desk every weekday at 08:30 IST = 03:00 UTC):
#   crontab -e
#   30 8 * * 1-5 /full/path/to/scripts/run_desk_cron.sh
#
# cron runs with a bare environment, so we cd to the project and use absolute
# paths via this script's own location.

set -euo pipefail

# Directory of this script -> project root is its parent.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Tickers to analyze each run. Edit this list as you like.
TICKERS=("BEL.NS" "HAL.NS")

LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/desk-$(date +%Y-%m-%d).log"

# shellcheck disable=SC1091
source "$PROJECT_DIR/venv/bin/activate"

echo "===== cron run $(date -u +%Y-%m-%dT%H:%M:%SZ) =====" >> "$LOG_FILE"
python -m src.run "${TICKERS[@]}" >> "$LOG_FILE" 2>&1
echo "===== done $(date -u +%Y-%m-%dT%H:%M:%SZ) =====" >> "$LOG_FILE"
