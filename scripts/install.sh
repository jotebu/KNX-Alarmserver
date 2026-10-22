#!/usr/bin/env bash
# Install the checked-out source, preserving config and persistent data.
set -Eeuo pipefail
# Release code and venv must remain readable/executable for the service account.
# Private settings and data directories use explicit restrictive modes below.
umask 0022
[[ $EUID -eq 0 ]] || { echo 'Bitte mit sudo bash scripts/install.sh starten.' >&2; exit 1; }
enable_lan=false
listen_port=
while [[ $# -gt 0 ]]; do
  case $1 in
    --lan) enable_lan=true; shift ;;
    --port)
      [[ $# -ge 2 && $2 =~ ^[0-9]{1,5}$ ]] || { echo 'Port zwischen 1 und 65535 erforderlich.' >&2; exit 1; }
      listen_port=$((10#$2))
      (( listen_port >= 1 && listen_port <= 65535 )) || { echo 'Port zwischen 1 und 65535 erforderlich.' >&2; exit 1; }
      shift 2 ;;
    *) echo 'Aufruf: sudo bash scripts/install.sh [--lan] [--port PORT]' >&2; exit 1 ;;
  esac
done
exec 9>/run/lock/knx-alarmserver-install.lock
flock -n 9 || { echo 'Eine Installation laeuft bereits.' >&2; exit 1; }
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
base=/opt/knx-alarmserver
settings=/etc/knx-alarmserver
data=/var/lib/knx-alarmserver
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3 python3-venv python3-pip ca-certificates git curl
python3 -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11 oder neuer erforderlich"'
getent passwd knx-alarmserver >/dev/null || useradd --system --home-dir "$data" --shell /usr/sbin/nologin knx-alarmserver
install -d -m 0755 "$base" "$base/releases"
install -d -m 0750 -o root -g knx-alarmserver "$settings"
install -d -m 0700 -o knx-alarmserver -g knx-alarmserver "$data" "$data/backups"
[[ -f $settings/config.toml ]] || install -m 0640 -o root -g knx-alarmserver "$source_dir/config/config.example.toml" "$settings/config.toml"
[[ -f $settings/alarms.csv ]] || install -m 0640 -o root -g knx-alarmserver "$source_dir/config/alarms.csv" "$settings/alarms.csv"
stage=$(mktemp -d "$base/releases/release-XXXXXXXX")
chmod 0755 "$stage"
install -d "$stage/source"
tar -C "$source_dir" --exclude=.git --exclude=.venv --exclude=.test-deps --exclude=__pycache__ --exclude='*.egg-info' --exclude=dist --exclude=build --exclude='*.local.*' --exclude='*.sqlite3*' --exclude='*.knxkeys' -cf - . | tar -C "$stage/source" -xf -
python3 -m venv "$stage/venv"
"$stage/venv/bin/pip" install --disable-pip-version-check "$stage/source"
"$stage/venv/bin/pip" check
listener_options=()
if $enable_lan; then listener_options+=(--lan); fi
if [[ -n $listen_port ]]; then listener_options+=(--port "$listen_port"); fi
runuser -u knx-alarmserver -- "$stage/venv/bin/knx-alarmserver" -c "$settings/config.toml" check
# Consistent backup, including WAL pages, before starting new code.
db_path=$(python3 -c 'import sys,tomllib,pathlib; p=pathlib.Path(sys.argv[1]); c=tomllib.loads(p.read_text()); print((p.parent / c["server"]["database"]).resolve())' "$settings/config.toml")
if [[ -f $db_path ]]; then
  backup_path="$data/backups/before-update-$(date -u +%Y%m%dT%H%M%S)-$$.sqlite3"
  runuser -u knx-alarmserver -- python3 - "$db_path" "$backup_path" <<'PY'
import sqlite3, sys
with sqlite3.connect(sys.argv[1]) as source, sqlite3.connect(sys.argv[2]) as target:
    source.backup(target)
PY
fi
# Create first account interactively. No default or command-line passwords.
has_users=$(python3 - "$db_path" <<'PY'
from pathlib import Path
import sqlite3,sys
p=Path(sys.argv[1])
try:
    with sqlite3.connect(f'file:{p}?mode=ro',uri=True) as db:
        print(int(db.execute('SELECT EXISTS(SELECT 1 FROM users)').fetchone()[0]))
except sqlite3.Error:
    print(0)
PY
)
if [[ $has_users == 0 ]]; then
  read -r -p 'E-Mail-Adresse des ersten Admins: ' initial_admin_email
  runuser -u knx-alarmserver -- "$stage/venv/bin/knx-alarmserver" -c "$settings/config.toml" user-add "$initial_admin_email" --role admin
fi
previous=$(readlink -f "$base/current" || true)
had_unit=false
if [[ -f /etc/systemd/system/knx-alarmserver.service ]]; then
  cp /etc/systemd/system/knx-alarmserver.service "$stage/previous.service"
  had_unit=true
fi
rollback() {
  trap - ERR
  echo 'Start fehlgeschlagen. Vorherige Programmversion wird wieder aktiviert.' >&2
  if [[ -n $previous ]]; then
    ln -s "$previous" "$base/current.rollback"
    mv -Tf "$base/current.rollback" "$base/current"
  else
    systemctl stop knx-alarmserver || true
    rm -f -- "$base/current"
  fi
  if $had_unit; then cp "$stage/previous.service" /etc/systemd/system/knx-alarmserver.service; fi
  if [[ -f $stage/listener-before.toml ]]; then
    cp "$stage/listener-before.toml" "$settings/config.toml"
  fi
  systemctl daemon-reload
  if [[ -n $previous ]]; then systemctl restart knx-alarmserver || true; fi
  echo 'Datenbank wird nicht automatisch zurueckgesetzt; Backup liegt unter /var/lib/knx-alarmserver/backups.' >&2
  exit 1
}
trap rollback ERR
if [[ ${#listener_options[@]} -gt 0 ]]; then
  cp -p "$settings/config.toml" "$stage/listener-before.toml"
  chmod 0600 "$stage/listener-before.toml"
  python3 "$stage/source/scripts/enable_lan.py" "$settings/config.toml" "${listener_options[@]}"
fi
ln -s "$stage" "$base/current.new"
mv -Tf "$base/current.new" "$base/current"
install -m 0644 "$stage/source/systemd/knx-alarmserver.service" /etc/systemd/system/knx-alarmserver.service
install -d -m 0755 -o root -g root /usr/local/libexec
install -m 0644 -o root -g root "$stage/source/scripts/dashboard_update.py" /usr/local/libexec/knx-alarmserver-update.py
install -m 0644 -o root -g root "$stage/source/systemd/knx-alarmserver-update.service" /etc/systemd/system/knx-alarmserver-update.service
install -m 0644 -o root -g root "$stage/source/systemd/knx-alarmserver-update.path" /etc/systemd/system/knx-alarmserver-update.path
systemctl daemon-reload
if systemctl cat knx-alarmserver.service >/dev/null 2>&1; then
  systemctl reset-failed knx-alarmserver || true
fi
systemctl enable knx-alarmserver
systemctl restart knx-alarmserver
# Liveness only: KNX is deliberately disabled on first install.
python3 - "$settings/config.toml" "$stage/source/pyproject.toml" <<'PY'
import json,sys,time,tomllib,urllib.request
with open(sys.argv[1],'rb') as handle: server=tomllib.load(handle)['server']
with open(sys.argv[2],'rb') as handle: expected_version=tomllib.load(handle)['project']['version']
host=server.get('host','127.0.0.1')
host='127.0.0.1' if host=='0.0.0.0' else host
host='[::1]' if host=='::' else f'[{host}]' if ':' in host else host
url=f'http://{host}:{server.get("port",80)}/health/live'
for attempt in range(30):
    try:
        with urllib.request.urlopen(url,timeout=1) as response:
            state=json.load(response)
            if state['status']=='ok' and state['version']==expected_version: break
    except (OSError,ValueError): pass
    time.sleep(1)
else: raise SystemExit('Webdienst antwortet nicht')
PY
systemctl enable --now knx-alarmserver-update.path
trap - ERR
if [[ -n $previous ]]; then
  ln -s "$previous" "$base/previous.new"
  mv -Tf "$base/previous.new" "$base/previous"
fi
echo 'Installation erfolgreich. Webadresse gemaess host/port in /etc/knx-alarmserver/config.toml; LAN-Vorgabe: http://RASPBERRY-IP'
echo 'Konfiguration: /etc/knx-alarmserver/config.toml | Protokoll: journalctl -u knx-alarmserver -f'

