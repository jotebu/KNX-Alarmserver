#!/usr/bin/env bash
# Enable signed ARM64 web-dashboard updates for an existing binary installation.
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo "Bitte mit sudo bash ausfuehren." >&2; exit 1; }
[[ $(uname -m) == aarch64 ]] || { echo "Linux ARM64 erforderlich." >&2; exit 1; }
base=/opt/knx-alarmserver/current
[[ -f $base/BUILD-VERSION.txt && -x $base/nuitka_entry.dist/knx-alarmserver ]] || {
  echo "Keine kompatible Binärinstallation gefunden. Installation unveraendert." >&2; exit 1;
}
systemctl is-active --quiet knx-alarmserver.service || { echo "Alarmserver ist nicht aktiv." >&2; exit 1; }
if [[ -e /usr/local/libexec/knx-alarmserver-update.py ]]; then
  echo "Bestehenden Update-Worker nicht ueberschreiben. Manuell pruefen." >&2
  exit 1
fi
apt-get update
apt-get install -y ca-certificates curl python3 python3-cryptography
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
# Pin the bootstrapper's worker revision, rather than fetching mutable main.
worker_sha=5d0dd96c28912ae5c79340b48fb4c425c1a3ef49
curl --proto '=https' --tlsv1.2 -fsSL --retry 3 \
  "https://raw.githubusercontent.com/jotebu/KNX-Alarmserver/$worker_sha/scripts/bin-update.py" \
  -o "$work/bin-update.py"
python3 -m py_compile "$work/bin-update.py"
install -d -m 0755 -o root -g root /usr/local/libexec
install -m 0644 -o root -g root "$work/bin-update.py" /usr/local/libexec/knx-alarmserver-update.py
cat > /etc/systemd/system/knx-alarmserver-update.service <<'UNIT'
[Unit]
Description=KNX Alarmserver signed ARM64 update
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
User=root
Group=root
ExecStart=/usr/bin/python3 -I /usr/local/libexec/knx-alarmserver-update.py
ExecStopPost=/usr/bin/python3 -I /usr/local/libexec/knx-alarmserver-update.py --finish
RuntimeDirectory=knx-alarmserver-update
RuntimeDirectoryMode=0755
RuntimeDirectoryPreserve=yes
TimeoutStartSec=30min
UMask=0022
StandardInput=null
StandardOutput=journal
StandardError=journal
UNIT
cat > /etc/systemd/system/knx-alarmserver-update.path <<'UNIT'
[Unit]
Description=Watch KNX Alarmserver dashboard update requests

[Path]
PathExists=/var/lib/knx-alarmserver/update-request
Unit=knx-alarmserver-update.service

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now knx-alarmserver-update.path
echo "Update-Dienst eingerichtet, keine Anwendung neu gestartet."
systemctl is-active knx-alarmserver-update.path
