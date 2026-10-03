#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
root_dir="$PWD"
[[ "$(id -u)" == 0 ]] || { echo 'Run this script as root or with sudo.' >&2; exit 1; }
command -v systemctl >/dev/null || { echo 'systemd unavailable; schedule scripts/renew_https.sh with your scheduler twice daily.' >&2; exit 1; }
[[ -f .https-state/letsencrypt/live/sunfan88.com/fullchain.pem ]]
# Verify the ACME renewal path and deploy hook before enabling the timer.
bash scripts/renew_https.sh --dry-run --run-deploy-hooks
cat > /etc/systemd/system/pear-admin-https-renew.service <<EOF
[Unit]
Description=Renew sunfan88.com TLS certificate and reload Nginx
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/bin/bash "$root_dir/scripts/renew_https.sh"
EOF
cat > /etc/systemd/system/pear-admin-https-renew.timer <<'EOF'
[Unit]
Description=Check sunfan88.com certificate twice daily

[Timer]
OnCalendar=*-*-* 03,15:23:00
RandomizedDelaySec=3600
Persistent=true

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now pear-admin-https-renew.timer
systemctl list-timers pear-admin-https-renew.timer --no-pager
