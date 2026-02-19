#!/bin/bash
# run.sh - Wrapper script for running anny-booking-automation via cron on Linux.
# Place a cron entry like this (runs at 23:58 every night):
#   58 23 * * * /path/to/anny-booking-automation/scripts/run.sh >> /path/to/anny-booking-automation/logs/cron.log 2>&1

set -e

# Resolve absolute path to repo root (one level above this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

cd "$REPO_DIR"

# Activate virtual environment
source "$REPO_DIR/venv/bin/activate"

# Run the booking script
python main.py
