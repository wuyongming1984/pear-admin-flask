#!/usr/bin/env bash
# Enable TLS in an existing Docker deployment. Never rebuild web or touch MySQL.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
root_dir="$PWD"
email="${1:-}"
if [[ $# != 1 || ! "$email" =~ ^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$ ]]; then
  echo 'Usage: bash scripts/setup_https.sh certificate-contact@example.com' >&2
  exit 2
fi
for tool in docker curl openssl cmp getent; do
  command -v "$tool" >/dev/null || { echo "Required: $tool" >&2; exit 1; }
done
[[ -f .env && -f docker-compose.yml ]] || { echo 'Existing deployment and .env required.' >&2; exit 1; }
if docker compose version >/dev/null 2>&1; then
  compose=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  compose=(docker-compose)
else
  echo 'Docker Compose is required.' >&2; exit 1
fi
# Use exactly the existing project's base file and our managed override.
base_compose=("${compose[@]}" -f docker-compose.yml)
active_compose=("${compose[@]}" -f docker-compose.yml -f docker-compose.override.yml)
if [[ -e docker-compose.override.yml ]] && ! cmp -s docker-compose.https.yml docker-compose.override.yml; then
  echo 'Custom docker-compose.override.yml exists; stopped without replacing it.' >&2
  exit 1
fi
if [[ -n "${COMPOSE_FILE:-}" ]]; then
  echo 'Unset COMPOSE_FILE before setup; review custom Compose files separately.' >&2
  exit 1
fi
domains=(www.sunfan88.com)
case "${HTTPS_INCLUDE_APEX:-false}" in
  true) domains+=(sunfan88.com) ;;
  false) ;;
  *) echo 'HTTPS_INCLUDE_APEX must be true or false.' >&2; exit 2 ;;
esac
certbot_domains=()
for domain in "${domains[@]}"; do
  # Stop before touching the gateway when a requested name has no DNS address.
  getent ahosts "$domain" >/dev/null || {
    echo "No usable DNS address for $domain; the gateway was not changed." >&2; exit 1;
  }
  certbot_domains+=(-d "$domain")
done
"${base_compose[@]}" config --quiet
for service in web nginx; do
  container_id="$("${base_compose[@]}" ps -q "$service")"
  [[ -n "$container_id" && "$(docker inspect -f '{{.State.Running}}' "$container_id")" == true ]] || {
    echo "The existing $service service must be running." >&2; exit 1;
  }
done

certbot_image="${CERTBOT_IMAGE:-certbot/certbot:latest}"
docker pull "$certbot_image"
mkdir -p .https-state/nginx .https-state/www/.well-known/acme-challenge .https-state/letsencrypt .https-state/logs
chmod 700 .https-state/letsencrypt
backup_dir=".https-state/backups/$(date -u +%Y%m%dT%H%M%SZ)-$$"
mkdir -p "$backup_dir"
for config in docker-compose.override.yml .https-state/nginx/default.conf .https-state/nginx/http-mode.conf; do
  if [[ -f "$config" ]]; then cp -- "$config" "$backup_dir/$(basename -- "$config")"; fi
done
rollback() {
  code=$?
  trap - EXIT
  if [[ "$code" != 0 ]]; then
    echo "HTTPS setup failed; restoring the previous gateway. Backup: $root_dir/$backup_dir" >&2
    if [[ -f "$backup_dir/docker-compose.override.yml" ]]; then
      cp -- "$backup_dir/docker-compose.override.yml" docker-compose.override.yml
    else
      rm -f -- docker-compose.override.yml
    fi
    for name in default.conf http-mode.conf; do
      if [[ -f "$backup_dir/$name" ]]; then cp -- "$backup_dir/$name" ".https-state/nginx/$name"; fi
    done
    # Recreate only the gateway to restore its previous port/volume mappings.
    if [[ -f docker-compose.override.yml ]]; then
      "${active_compose[@]}" up -d --no-deps --force-recreate nginx || echo 'Gateway rollback failed; inspect Docker logs.' >&2
    else
      "${base_compose[@]}" up -d --no-deps --force-recreate nginx || echo 'Gateway rollback failed; inspect Docker logs.' >&2
    fi
  fi
  exit "$code"
}
trap rollback EXIT

cp -- docker-compose.https.yml docker-compose.override.yml
printf 'include /etc/nginx/pear/app.locations.conf;\n' > .https-state/nginx/http-mode.conf
cp -- nginx/nginx.http.conf .https-state/nginx/default.conf
"${active_compose[@]}" config --quiet
"${active_compose[@]}" run --rm --no-deps -T nginx nginx -t
"${active_compose[@]}" up -d --no-deps --force-recreate nginx

# Confirm the challenge path publicly, with no redirects and no insecure TLS.
token="pear-https-check-$(date +%s)-$$"
printf '%s' "$token" > ".https-state/www/.well-known/acme-challenge/$token"
for domain in "${domains[@]}"; do
  response="$(curl --noproxy '*' -fsS --retry 3 --retry-connrefused --connect-timeout 5 --max-time 15 "http://$domain/.well-known/acme-challenge/$token")"
  [[ "$response" == "$token" ]] || { echo "Public ACME path failed for $domain. Check DNS/port 80." >&2; exit 1; }
done
rm -f -- ".https-state/www/.well-known/acme-challenge/$token"

docker run --rm \
  -v "$root_dir/.https-state/letsencrypt:/etc/letsencrypt" \
  -v "$root_dir/.https-state/www:/var/www/certbot" \
  -v "$root_dir/.https-state/logs:/var/log/letsencrypt" \
  "$certbot_image" certonly --non-interactive --agree-tos --email "$email" \
  --webroot -w /var/www/certbot --cert-name sunfan88.com \
  "${certbot_domains[@]}" --expand --keep-until-expiring
cert_path=.https-state/letsencrypt/live/sunfan88.com/fullchain.pem
[[ -s "$cert_path" && -s .https-state/letsencrypt/live/sunfan88.com/privkey.pem ]]
openssl x509 -in "$cert_path" -noout -checkend 86400
for domain in "${domains[@]}"; do
  openssl x509 -in "$cert_path" -noout -checkhost "$domain"
done

# Test the candidate without stopping the gateway. CLI volume overrides the
# Compose mount at the same target; application networks remain unchanged.
sed "s/server_name www.sunfan88.com;/server_name ${domains[*]};/" \
  nginx/nginx.https.conf > .https-state/nginx/candidate.conf
"${active_compose[@]}" run --rm --no-deps -T \
  -v "$root_dir/.https-state/nginx/candidate.conf:/etc/nginx/conf.d/default.conf:ro" nginx nginx -t
# cp preserves the inode of the existing single-file bind mount.
cp -- .https-state/nginx/candidate.conf .https-state/nginx/default.conf
"${active_compose[@]}" exec -T nginx nginx -t
"${active_compose[@]}" exec -T nginx nginx -s reload
# Reload signals the master asynchronously. Docker may accept host port 443
# before the new Nginx listener is ready, returning TLS EOF rather than refusal.
verify_https() {
  local scope="$1" domain="$2" attempt status
  shift 2
  printf 'Checking %s HTTPS for %s...\n' "$scope" "$domain"
  for attempt in 1 2 3 4 5; do
    if curl --noproxy '*' -fsS --connect-timeout 5 --max-time 15 \
      "$@" "https://$domain/pc/" -o /dev/null; then
      return 0
    else
      status=$?
    fi
    # Retry connection/handshake failures only. Trust and HTTP errors stop here.
    case "$status" in
      7|28|35|52|56) ;;
      *) break ;;
    esac
    if [[ "$attempt" -lt 5 ]]; then
      printf '%s HTTPS not ready for %s (curl %s, attempt %s/5); retrying...\n' \
        "$scope" "$domain" "$status" "$attempt" >&2
      sleep 1
    fi
  done
  printf '%s HTTPS verification failed for %s (curl %s).\n' "$scope" "$domain" "$status" >&2
  "${active_compose[@]}" logs --no-color --tail 40 nginx >&2 || true
  return "$status"
}
for domain in "${domains[@]}"; do
  verify_https local "$domain" --resolve "$domain:443:127.0.0.1"
  verify_https public "$domain"
done

# Enable the requested 301 only after working public HTTPS has been established.
printf 'location / { return 301 https://www.sunfan88.com$request_uri; }\n' > .https-state/nginx/http-mode.conf
"${active_compose[@]}" exec -T nginx nginx -t
"${active_compose[@]}" exec -T nginx nginx -s reload
for domain in "${domains[@]}"; do
  result="$(curl --noproxy '*' -sS --retry 3 --retry-delay 1 --connect-timeout 5 --max-time 15 \
    -o /dev/null -w '%{http_code} %{redirect_url}' "http://$domain/pc/?https-check=1")"
  # Allow Nginx workers a moment to switch configurations after reload.
  for attempt in 1 2 3; do
    [[ "$result" == '301 https://www.sunfan88.com/pc/?https-check=1' ]] && break
    sleep 1
    result="$(curl --noproxy '*' -sS --connect-timeout 5 --max-time 15 -o /dev/null \
      -w '%{http_code} %{redirect_url}' "http://$domain/pc/?https-check=1")"
  done
  [[ "$result" == '301 https://www.sunfan88.com/pc/?https-check=1' ]] || { echo "HTTP redirect verification failed: $domain" >&2; exit 1; }
done
trap - EXIT
printf '\nHTTPS and HTTP 301 verified from this server. Confirm again from an external client.\n'
printf 'Install renewal next: sudo bash scripts/install_https_renewal.sh\n'
printf 'Backup: %s/%s\n' "$root_dir" "$backup_dir"
