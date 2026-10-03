#!/usr/bin/env bash
# Isolated command stubs test transaction ordering, rollback and renewal hooks.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source_dir="$PWD"
test_root="${1:?Usage: bash tests/verify_https_scripts.sh /path/to/test-output}"
mkdir -p "$test_root/bin"
test_root="$(cd -- "$test_root" && pwd)"
cat > "$test_root/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -eu
printf '%s\n' "$*" >> "$PWD/commands.log"
if [[ "$1" == inspect ]]; then echo true; exit; fi
if [[ "$1" == pull ]]; then exit; fi
if [[ "$1" == run ]]; then
  if [[ "$*" == *certonly* ]]; then
    [[ "${TEST_MODE:-}" != cert-fails ]] || exit 1
    mkdir -p .https-state/letsencrypt/live/sunfan88.com
    printf certificate > .https-state/letsencrypt/live/sunfan88.com/fullchain.pem
    printf key > .https-state/letsencrypt/live/sunfan88.com/privkey.pem
  elif [[ "${TEST_MODE:-}" == renew-changes || "${TEST_MODE:-}" == reload-fails ]]; then
    touch .https-state/letsencrypt/.nginx-reload-needed
  fi
  exit
fi
if [[ "$*" == *'ps -q '* ]]; then echo container; fi
if [[ "${TEST_MODE:-}" == reload-fails && "$*" == *'nginx -s reload'* ]]; then exit 1; fi
EOF
cat > "$test_root/bin/curl" <<'EOF'
#!/usr/bin/env bash
set -eu
printf '%s\n' "$*" >> "$PWD/curl.log"
if [[ "$*" == *https://* ]]; then
  scope=public
  [[ "$*" != *--resolve* ]] || scope=local
  counter_file="$PWD/$scope-probes"
  count=0
  [[ ! -f "$counter_file" ]] || count="$(cat "$counter_file")"
  count=$((count + 1))
  printf '%s\n' "$count" > "$counter_file"
  if [[ "${TEST_MODE:-}" == "$scope-tls-starting" && "$count" -le 2 ]] ||
     [[ "${TEST_MODE:-}" == local-tls-eof && "$scope" == local ]]; then
    echo 'curl: (35) unexpected eof while reading' >&2; exit 35
  fi
  if [[ "${TEST_MODE:-}" == untrusted-cert && "$scope" == local ]]; then exit 60; fi
fi
if [[ "${TEST_MODE:-}" == apex-unresolved && "$*" == *http://sunfan88.com/* ]]; then
  echo 'curl: (6) Could not resolve host: sunfan88.com' >&2; exit 6
fi
if [[ "$*" == *acme-challenge* ]]; then
  for arg in "$@"; do
    if [[ "$arg" == http://* ]]; then cat ".https-state/www/.well-known/acme-challenge/${arg##*/}"; exit; fi
  done
fi
if [[ "${TEST_MODE:-}" == public-tls-fails && "$*" == *https://* && "$*" != *--resolve* ]]; then exit 28; fi
if [[ "$*" == *'%{http_code}'* ]]; then
  if [[ "$(cat .https-state/nginx/http-mode.conf)" == *'return 301'* ]]; then
    printf '301 https://www.sunfan88.com/pc/?https-check=1'
  else
    printf '200 '
  fi
fi
EOF
printf '#!/usr/bin/env bash\nexit 0\n' > "$test_root/bin/openssl"
cat > "$test_root/bin/getent" <<'EOF'
#!/usr/bin/env bash
set -eu
printf '%s\n' "$*" >> "$PWD/dns.log"
if [[ "${TEST_MODE:-}" == www-unresolved ]]; then exit 2; fi
if [[ "${TEST_MODE:-}" == apex-unresolved && "$*" == *' sunfan88.com' ]]; then exit 2; fi
printf '8.159.138.234 STREAM %s\n' "${@: -1}"
EOF
chmod +x "$test_root/bin/"*
export PATH="$test_root/bin:$PATH"
export CERTBOT_IMAGE=certbot-test-only
prepare() {
  case_dir="$test_root/$1"
  mkdir -p "$case_dir/scripts" "$case_dir/nginx"
  cp "$source_dir/scripts/setup_https.sh" "$source_dir/scripts/renew_https.sh" "$case_dir/scripts/"
  cp "$source_dir/nginx/"*.conf "$case_dir/nginx/"
  cp "$source_dir/docker-compose.yml" "$source_dir/docker-compose.https.yml" "$case_dir/"
  : > "$case_dir/.env"
  cd -- "$case_dir"
}
prepare success
TEST_MODE=success bash scripts/setup_https.sh test@example.com >/dev/null
cmp -s docker-compose.https.yml docker-compose.override.yml
rg -q 'return 301' .https-state/nginx/http-mode.conf
rg -q 'https://www.sunfan88.com/pc/' curl.log
printf 'PASS: setup verifies TLS before enabling 301\n'

prepare onlywww
TEST_MODE=apex-unresolved bash scripts/setup_https.sh test@example.com >/dev/null
cmp -s docker-compose.https.yml docker-compose.override.yml
rg -q 'return 301' .https-state/nginx/http-mode.conf
! rg -q -- '-d sunfan88.com' commands.log
printf 'PASS: missing apex DNS does not block canonical www HTTPS\n'

prepare unresolvedwww
if TEST_MODE=www-unresolved bash scripts/setup_https.sh test@example.com >/dev/null 2>&1; then exit 1; fi
[[ ! -d .https-state ]]
! rg -q 'up -d' commands.log
printf 'PASS: canonical DNS failure stops before changing the gateway\n'

prepare optionalapex
HTTPS_INCLUDE_APEX=true TEST_MODE=success bash scripts/setup_https.sh test@example.com >/dev/null
rg -q -- '-d sunfan88.com' commands.log
rg -q 'server_name www.sunfan88.com sunfan88.com;' .https-state/nginx/candidate.conf
printf 'PASS: explicit apex option includes both certificate names\n'

prepare unresolvedapex
if HTTPS_INCLUDE_APEX=true TEST_MODE=apex-unresolved bash scripts/setup_https.sh test@example.com >/dev/null 2>&1; then exit 1; fi
[[ ! -d .https-state ]]
printf 'PASS: requested apex DNS failure stops before changing the gateway\n'

prepare localstarting
TEST_MODE=local-tls-starting bash scripts/setup_https.sh test@example.com >setup.log 2>&1
[[ "$(cat local-probes)" == 3 ]]
rg -q 'return 301' .https-state/nginx/http-mode.conf
printf 'PASS: transient local TLS EOF waits for the listener before enabling 301\n'

prepare publicstarting
TEST_MODE=public-tls-starting bash scripts/setup_https.sh test@example.com >setup.log 2>&1
[[ "$(cat public-probes)" == 3 ]]
rg -q 'return 301' .https-state/nginx/http-mode.conf
printf 'PASS: transient public TLS failure is retried before enabling 301\n'

prepare persistentlocaleof
if TEST_MODE=local-tls-eof bash scripts/setup_https.sh test@example.com >setup.log 2>&1; then exit 1; fi
[[ "$(cat local-probes)" == 5 ]]
[[ ! -f public-probes && ! -e docker-compose.override.yml ]]
! rg -q 'return 301' .https-state/nginx/http-mode.conf
rg -q 'local.*www.sunfan88.com' setup.log
rg -q 'logs --no-color --tail 40 nginx' commands.log
printf 'PASS: persistent local TLS EOF stops after bounded retries and rolls back\n'

prepare untrustedcert
if TEST_MODE=untrusted-cert bash scripts/setup_https.sh test@example.com >setup.log 2>&1; then exit 1; fi
[[ "$(cat local-probes)" == 1 ]]
[[ ! -e docker-compose.override.yml ]]
! rg -q 'return 301' .https-state/nginx/http-mode.conf
printf 'PASS: certificate trust failure immediately rolls back without enabling 301\n'

prepare blocked443
if TEST_MODE=public-tls-fails bash scripts/setup_https.sh test@example.com >/dev/null 2>&1; then exit 1; fi
[[ ! -e docker-compose.override.yml ]]
! rg -q 'return 301' .https-state/nginx/http-mode.conf
rg -q 'up -d --no-deps --force-recreate nginx' commands.log
printf 'PASS: blocked public 443 restores the original gateway without enabling 301\n'

prepare certfailure
if TEST_MODE=cert-fails bash scripts/setup_https.sh test@example.com >/dev/null 2>&1; then exit 1; fi
[[ ! -e docker-compose.override.yml ]]
printf 'PASS: certificate failure restores the original gateway\n'

prepare previoushttps
cp docker-compose.https.yml docker-compose.override.yml
mkdir -p .https-state/nginx
printf 'previous nginx' > .https-state/nginx/default.conf
printf 'previous redirect' > .https-state/nginx/http-mode.conf
if TEST_MODE=public-tls-fails bash scripts/setup_https.sh test@example.com >/dev/null 2>&1; then exit 1; fi
[[ "$(cat .https-state/nginx/default.conf)" == 'previous nginx' ]]
[[ "$(cat .https-state/nginx/http-mode.conf)" == 'previous redirect' ]]
cmp -s docker-compose.https.yml docker-compose.override.yml
printf 'PASS: failed reconfiguration restores a previous HTTPS deployment\n'

prepare customoverride
printf 'custom override' > docker-compose.override.yml
if TEST_MODE=success bash scripts/setup_https.sh test@example.com >/dev/null 2>&1; then exit 1; fi
[[ "$(cat docker-compose.override.yml)" == 'custom override' ]]
[[ ! -d .https-state ]]
printf 'PASS: custom override is preserved\n'

cd "$test_root/success"
: > commands.log
TEST_MODE=renew-no-change bash scripts/renew_https.sh
! rg -q 'nginx -s reload' commands.log
printf 'PASS: unchanged certificate does not reload Nginx\n'
TEST_MODE=renew-changes bash scripts/renew_https.sh
rg -q 'nginx -s reload' commands.log
[[ ! -f .https-state/letsencrypt/.nginx-reload-needed ]]
printf 'PASS: successful renewal reloads Nginx and clears the marker\n'
if TEST_MODE=reload-fails bash scripts/renew_https.sh; then exit 1; fi
[[ -f .https-state/letsencrypt/.nginx-reload-needed ]]
printf 'PASS: failed reload retains its marker for retry\n'
