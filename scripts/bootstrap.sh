#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt

dest="$HOME/Library/LaunchAgents/co.ttvl.trmnlhealth.plist"
mkdir -p "$(dirname "$dest")"
cp launchd/co.ttvl.trmnlhealth.plist "$dest"

launchctl unload "$dest" >/dev/null 2>&1 || true
launchctl load "$dest"

echo "launchd agent co.ttvl.trmnlhealth loaded (runs hourly at :30)."
echo "Logs: $HOME/Library/Logs/trmnl_health.log"
