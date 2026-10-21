#!/usr/bin/env bash
# Explicit version only. Never reset a working checkout or deploy arbitrary main.
set -Eeuo pipefail
[[ $EUID -eq 0 ]] || { echo 'Bitte mit sudo starten.' >&2; exit 1; }
version=${1:-}
[[ $version =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo 'Aufruf: sudo bash update.sh v0.1.1' >&2; exit 1; }
work_dir=$(mktemp -d /tmp/knx-alarmserver-update-XXXXXXXX)
trap 'rm -rf -- "$work_dir"' EXIT
git clone --depth 1 --branch "$version" https://github.com/jotebu/KNX-Alarmserver.git "$work_dir/source"
python3 - "$work_dir/source/pyproject.toml" "${version#v}" <<'PY'
import sys,tomllib
with open(sys.argv[1],'rb') as handle: version=tomllib.load(handle)['project']['version']
if version!=sys.argv[2]: raise SystemExit('Tag und Paketversion stimmen nicht ueberein')
PY
bash "$work_dir/source/scripts/install.sh"
