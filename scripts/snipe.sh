#!/usr/bin/env bash
cd "$(dirname "$0")/.."
exec 9>/tmp/anny-sniper.lock
flock -n 9 || exit 0
source venv/bin/activate
python3 main.py >> logs/sniper.log 2>&1
