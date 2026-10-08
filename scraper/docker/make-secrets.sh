#!/usr/bin/env bash
# Build the SCRAPER_SECRETS_B64 bundle from a .env file.
#
#   scraper/docker/make-secrets.sh [path-to-.env]   # default: repo-root .env
#
# Prints a single line of base64 on stdout. Warnings (key names only, never
# values) go to stderr. Use it like:
#
#   docker run -e SCRAPER_SECRETS_B64="$(scraper/docker/make-secrets.sh)" ...
set -euo pipefail

REQUIRED=(DO_SPACES_ACCESS_KEY DO_SPACES_SECRET_KEY ANTHROPIC_API_KEY LEAGUESYNC_API_KEY TBA_KEY)
OPTIONAL=(ROBOTEVENTS_KEY)

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
env_file="${1:-$here/../../.env}"
if [ ! -f "$env_file" ]; then
  echo "make-secrets: env file not found: $env_file" >&2
  exit 1
fi

out=""
for key in "${REQUIRED[@]}" "${OPTIONAL[@]}"; do
  found=""
  value=""
  while IFS= read -r line || [ -n "$line" ]; do
    line="${line%$'\r'}"
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line#export }"
    if [[ "$line" == "$key="* ]]; then
      found=1
      value="${line#*=}"
    fi
  done <"$env_file"
  if [ -z "$found" ] || [ -z "$value" ]; then
    case " ${REQUIRED[*]} " in
      *" $key "*) echo "make-secrets: warning: $key missing or empty in $env_file" >&2 ;;
    esac
    continue
  fi
  out+="$key=$value"$'\n'
done

printf '%s' "$out" | base64 | tr -d '\n'
printf '\n'
