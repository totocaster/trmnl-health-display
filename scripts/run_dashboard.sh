#!/usr/bin/env bash
cd ~/Developer/trmnl_health || exit 1

LOG="$HOME/Library/Logs/trmnl_health.log"
PATH="/usr/local/bin:/usr/bin:/bin"

/usr/bin/env -i HOME="$HOME" PATH="$PATH" \
  /usr/bin/python3 -m trmnl_health publish --force >> "$LOG" 2>&1
