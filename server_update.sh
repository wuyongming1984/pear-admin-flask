#!/usr/bin/env bash
# Update an existing deployment without initializing or migrating its database.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

if [[ ! -f docker-compose.yml || ! -f .env ]]; then
  echo 'Run from an existing deployment with docker-compose.yml and .env.' >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  compose=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  compose=(docker-compose)
else
  echo 'Docker Compose is required.' >&2
  exit 1
fi

git pull --ff-only origin main
if [[ ! -s static/desktop/index.html ]]; then
  echo 'Built desktop assets are missing; update stopped.' >&2
  exit 1
fi

# An explicit caller override supports rollback; existing .env remains untouched.
export DESKTOP_DEFAULT="${DESKTOP_DEFAULT:-true}"
"${compose[@]}" config --quiet
"${compose[@]}" up -d --no-deps --build web
"${compose[@]}" ps web
printf '\nApplication update started. Check readiness with: docker logs --tail 50 pear_admin_web\n'
printf 'New desktop: http://www.sunfan88.com/pc/\nLegacy: http://www.sunfan88.com/legacy/\n'
