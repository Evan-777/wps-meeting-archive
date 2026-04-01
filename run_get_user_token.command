#!/bin/zsh
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -f "config.json" ]]; then
  echo "Missing config.json"
  echo "Copy config.example.json to config.json first, then fill your WPS credentials and webhooks."
  echo
  read -r "?Press Enter to close..."
  exit 1
fi

python3 -m wps_archive --config "$(pwd)/config.json" authorize-user
echo
read -r "?authorize-user finished. Press Enter to close..."
