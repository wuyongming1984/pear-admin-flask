#!/usr/bin/env bash
# Run the real updater with isolated Docker/Git boundaries; never contact a server.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
source_dir="$PWD"
test_root="${1:?Usage: bash tests/verify_server_update.sh /path/to/test-output}"
mkdir -p "$test_root/bin"
test_root="$(cd -- "$test_root" && pwd)"
cat > "$test_root/bin/git" <<'EOF'
#!/usr/bin/env bash
set -eu
[[ "$*" == 'pull --ff-only origin main' ]] || exit 90
printf 'git %s\n' "$*" >> commands.log
EOF
cat > "$test_root/bin/docker" <<'EOF'
#!/usr/bin/env bash
set -eu
printf 'docker %s\n' "$*" >> commands.log
[[ "$1" == compose ]] || exit 90
shift
if [[ "$1" == build && "${TEST_FAILURE:-}" == build ]]; then exit 20; fi
if [[ "$*" == *migrate_payment_audit.py* && "${TEST_FAILURE:-}" == migration ]]; then exit 21; fi
if [[ "$*" == *profile_editor_queries.py* && "${TEST_FAILURE:-}" == api ]]; then exit 22; fi
EOF
chmod +x "$test_root/bin/git" "$test_root/bin/docker"
export PATH="$test_root/bin:$PATH"
prepare() {
  mkdir -p "$test_root/$1/static/desktop"
  cp "$source_dir/server_update.sh" "$test_root/$1/"
  : > "$test_root/$1/docker-compose.yml"
  : > "$test_root/$1/.env"
  printf 'built desktop' > "$test_root/$1/static/desktop/index.html"
  cd -- "$test_root/$1"
}
prepare success
bash server_update.sh > update.log 2>&1
build_line="$(awk '/compose build web/{print NR}' commands.log)"
migrate_line="$(awk '/migrate_payment_audit.py --config prod/{print NR}' commands.log)"
verify_line="$(awk '/profile_editor_queries.py --config prod --scope documents/{print NR}' commands.log)"
start_line="$(awk '/compose up -d --no-deps web$/{print NR}' commands.log)"
[[ -n "$build_line" && -n "$migrate_line" && -n "$verify_line" && -n "$start_line" ]]
[[ "$build_line" -lt "$migrate_line" && "$migrate_line" -lt "$verify_line" && "$verify_line" -lt "$start_line" ]]
printf 'PASS: build, backed-up migration and real-database API checks precede web restart\n'
for failure in build migration api; do
  prepare "$failure-failure"
  if TEST_FAILURE="$failure" bash server_update.sh > update.log 2>&1; then
    echo "FAIL: $failure failure was ignored" >&2
    exit 1
  fi
  if awk '/compose up /{found=1} END {exit !found}' commands.log; then
    echo "FAIL: web restarted after $failure failure" >&2
    exit 1
  fi
  printf 'PASS: %s failure stops update before web restart\n' "$failure"
done
