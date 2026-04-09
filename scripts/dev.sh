#!/usr/bin/env bash
# dev.sh — Start the Astro development server.
#
# Usage: ./scripts/dev.sh [developer-name]
#
# Optionally loads dotconfig before starting the dev server.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DEVELOPER="${1:-${USER:-}}"

cd "$PROJECT_DIR"

# Load dotconfig if available
if command -v dotconfig &>/dev/null && [ -n "$DEVELOPER" ]; then
  echo "→ Loading dev config (dotconfig -d dev -l $DEVELOPER)..."
  dotconfig load -d dev -l "$DEVELOPER"
fi

echo "→ Starting Astro dev server..."
exec npm run dev
