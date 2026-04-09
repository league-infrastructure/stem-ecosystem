#!/usr/bin/env bash
# setup.sh — First-time project setup after cloning/forking this template.
#
# Usage: ./scripts/setup.sh [your-name]
#
# This script:
#   1. Installs Node.js dependencies
#   2. Creates your personal local config overrides (if dotconfig is available)
#   3. Optionally initializes rundbat for Docker deployment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DEVELOPER="${1:-}"

echo "=============================="
echo "  astro-template setup"
echo "=============================="
echo

cd "$PROJECT_DIR"

# ── 1. Node.js dependencies ────────────────────────────────────────────────────
echo "→ Installing Node.js dependencies..."
npm install
echo "  ✓ Dependencies installed"
echo

# ── 2. dotconfig local config ─────────────────────────────────────────────────
if command -v dotconfig &>/dev/null; then
  if [ -z "$DEVELOPER" ]; then
    DEVELOPER="${USER:-developer}"
  fi

  LOCAL_DIR="$PROJECT_DIR/config/local/$DEVELOPER"

  if [ ! -d "$LOCAL_DIR" ]; then
    echo "→ Creating local config for: $DEVELOPER"
    cp -r "$PROJECT_DIR/config/local/example" "$LOCAL_DIR"
    echo "  ✓ Created config/local/$DEVELOPER/"
    echo "  ℹ  Edit config/local/$DEVELOPER/public.env to set your local overrides"
    echo
  else
    echo "→ Local config already exists at config/local/$DEVELOPER/"
    echo
  fi

  echo "→ Loading dev config with dotconfig..."
  if dotconfig load -d dev -l "$DEVELOPER"; then
    echo "  ✓ .env file generated"
  else
    echo "  ✗ dotconfig load failed — check your config/local/$DEVELOPER/public.env"
  fi
  echo
else
  echo "ℹ  dotconfig is not installed — skipping config load."
  echo "   Install with: pipx install dotconfig"
  echo "   See: https://github.com/ericbusboom/dotconfig"
  echo
fi

# ── 3. rundbat (optional) ─────────────────────────────────────────────────────
if command -v rundbat &>/dev/null; then
  echo "→ rundbat detected. Running discovery..."
  rundbat discover || true
  echo
  echo "  ℹ  To set up a Docker deployment environment, run:"
  echo "     rundbat init"
  echo "     rundbat create-env dev"
  echo
else
  echo "ℹ  rundbat is not installed (optional, for Docker deployment)."
  echo "   Install with: pipx install rundbat"
  echo "   See: https://github.com/ericbusboom/rundbat"
  echo
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo "=============================="
echo "  Setup complete!"
echo "=============================="
echo
echo "Next steps:"
echo "  • Start the dev server:      npm run dev"
echo "  • Build for production:      npm run build"
echo "  • Run in Docker:             ./scripts/docker-run.sh"
echo
