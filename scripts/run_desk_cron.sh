#!/usr/bin/env bash
# The "alarm clock" script — what the scheduler (cron) runs automatically.
#
# Why a separate shell script instead of pointing cron straight at Python? Because
# cron starts with an almost-empty environment: no virtualenv, wrong folder. So
# this wrapper does the setup a human would do by hand — move into the project,
# turn on the venv — then runs the desk and saves the output to a dated log file.
#
# It activates the venv, runs the desk for the configured tickers, and appends
# output to a dated log. Delivery (email/Telegram) is on unless you add --no-send.
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
