#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
root_dir="$PWD"
[[ -f docker-compose.override.yml ]] && cmp -s docker-compose.https.yml docker-compose.override.yml || {
  echo 'Managed HTTPS override missing or changed; renewal stopped.' >&2; exit 1;
}
if docker compose version >/dev/null 2>&1; then
  compose=(docker compose -f docker-compose.yml -f docker-compose.override.yml)
else
  compose=(docker-compose -f docker-compose.yml -f docker-compose.override.yml)
fi
# Do not expose Docker's socket to the certificate container. The marker is
# created only by Certbot's successful-renewal deploy hook, including dry-runs.
marker=.https-state/letsencrypt/.nginx-reload-needed
docker run --rm \
  -v "$root_dir/.https-state/letsencrypt:/etc/letsencrypt" \
  -v "$root_dir/.https-state/www:/var/www/certbot" \
  -v "$root_dir/.https-state/logs:/var/log/letsencrypt" \
  "${CERTBOT_IMAGE:-certbot/certbot:latest}" renew --non-interactive --cert-name sunfan88.com \
  --deploy-hook 'touch /etc/letsencrypt/.nginx-reload-needed' "$@"
if [[ -f "$marker" ]]; then
  "${compose[@]}" exec -T nginx nginx -t
  "${compose[@]}" exec -T nginx nginx -s reload
  rm -f -- "$marker"
fi
