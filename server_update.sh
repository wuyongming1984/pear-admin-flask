#!/usr/bin/env bash
# Update an existing deployment, backing up and adding missing payment audit fields.
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
# 保留完整构建日志，让依赖下载超时等错误立即可见。
export BUILDKIT_PROGRESS="${BUILDKIT_PROGRESS:-plain}"
"${compose[@]}" config --quiet
"${compose[@]}" build web
# The one-off containers use the same .env and /app bind mount as the web service.
# Migration backs up ums_pay first and only adds the eight nullable audit fields.
# The mobile menu migration backs up menu settings and preserves existing grants.
# Any backup, migration or API failure stops the script before restarting web.
"${compose[@]}" run --rm --no-deps --entrypoint python web scripts/migrate_payment_audit.py --config prod
"${compose[@]}" run --rm --no-deps --entrypoint python web scripts/configure_mobile_workbench.py --config prod
"${compose[@]}" run --rm --no-deps --entrypoint python web scripts/migrate_payment_receipts.py --config prod
"${compose[@]}" run --rm --no-deps --entrypoint python web scripts/profile_editor_queries.py --config prod --scope documents
"${compose[@]}" up -d --no-deps web
"${compose[@]}" ps web
printf '\nApplication update started. Check readiness with: docker logs --tail 50 pear_admin_web\n'
printf 'New desktop: http://www.sunfan88.com/pc/\nLegacy: http://www.sunfan88.com/legacy/\n'
