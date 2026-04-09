#!/usr/bin/env bash
# docker-run.sh — Build and run the site in Docker using docker-compose.
#
# Usage: ./scripts/docker-run.sh [up|down|build|logs]
#
# Prerequisites:
#   • Docker installed and running
#   • A .env file (run ./scripts/setup.sh first, or dotconfig load -d dev)
#
# With rundbat:
#   rundbat start dev     — start containers
#   rundbat stop dev      — stop containers
#   rundbat health dev    — check container health

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMMAND="${1:-up}"

cd "$PROJECT_DIR"

# Load .env if present
if [ -f ".env" ]; then
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a
fi

COMPOSE_FILE="docker/docker-compose.yml"

case "$COMMAND" in
  up)
    echo "→ Starting containers..."
    docker compose -f "$COMPOSE_FILE" up --build -d
    echo "  ✓ Site running at http://localhost:${PORT:-8080}"
    ;;
  down)
    echo "→ Stopping containers..."
    docker compose -f "$COMPOSE_FILE" down
    ;;
  build)
    echo "→ Building Docker image..."
    docker compose -f "$COMPOSE_FILE" build
    ;;
  logs)
    docker compose -f "$COMPOSE_FILE" logs -f
    ;;
  *)
    echo "Usage: $0 [up|down|build|logs]"
    exit 1
    ;;
esac
