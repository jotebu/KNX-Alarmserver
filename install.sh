#!/usr/bin/env bash
# KNX Alarmserver - signed ARM64 first installation
set -Eeuo pipefail
umask 022
[[ $EUID == 0 ]] || { echo "Bitte mit sudo starten." >&2; exit 1; }
[[ $(uname -m) == aarch64 ]] || { echo "Linux ARM64 (aarch64) erforderlich." >&2; exit 1; }
for path in /opt/knx-alarmserver/current /etc/knx-alarmserver/config.toml /etc/systemd/system/knx-alarmserver.service /var/lib/knx-alarmserver/alarmserver.sqlite3; do
  [[ ! -e $path ]] || { echo "Vorhandene Installation erkannt: $path" >&2; exit 1; }
done
if ss -ltnH 'sport = :80' | grep -q .; then echo "Port 80 ist belegt." >&2; exit 1; fi
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl python3 python3-cryptography
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
curl --proto '=https' --tlsv1.2 -fsSL --retry 3 https://api.github.com/repos/jotebu/KNX-Alarmserver/releases/latest -o "$work/latest.json"
tag=$(python3 - "$work/latest.json" <<'PY'
import json,re,sys
r=json.load(open(sys.argv[1]))
tag=r.get("tag_name","")
assert re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+",tag),"Ungueltiger Tag"
assert {"arm64-release.json","knx-alarmserver-arm64-nuitka.tar.gz"} <= {a["name"] for a in r.get("assets",[])},"Release-Dateien fehlen"
print(tag)
PY
)
base="https://github.com/jotebu/KNX-Alarmserver/releases/download/$tag"
curl --proto '=https' --tlsv1.2 -fsSL --retry 3 "$base/arm64-release.json" -o "$work/arm64-release.json"
curl --proto '=https' --tlsv1.2 -fsSL --retry 3 "$base/knx-alarmserver-arm64-nuitka.tar.gz" -o "$work/knx-alarmserver-arm64-nuitka.tar.gz"
cat > "$work/release-public.pem" <<'PEM'
-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAL/KW5R+8mYsDxOlVJhXY6Wz56Ijvm6lU6DmK8gXUYD8=
-----END PUBLIC KEY-----
PEM
python3 - "$work" "${tag#v}" <<'PY'
import base64,hashlib,json,pathlib,re,sys,tarfile
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
work,expected=pathlib.Path(sys.argv[1]),sys.argv[2]
p=work/'arm64-release.json'
assert p.stat().st_size<=8192,"Manifest zu gross"
env=json.loads(p.read_text())
assert isinstance(env,dict) and set(env)=={'manifest','signature'},"Ungueltiges Signaturformat"
m=env['manifest']
assert isinstance(m,dict) and set(m)=={'format','version','platform','artifact','size','sha256'},"Manifestfelder ungueltig"
assert (m['format'],m['version'],m['platform'],m['artifact'])==('ASK-ARM64-RELEASE-1',expected,'linux-aarch64','knx-alarmserver-arm64-nuitka.tar.gz'),"Release-Identitaet ungueltig"
assert type(m['size']) is int and 0<m['size']<=512*1024*1024,"Groesse ungueltig"
assert isinstance(m['sha256'],str) and re.fullmatch('[0-9a-f]{64}',m['sha256']),"SHA256 ungueltig"
sig=env['signature']
assert isinstance(sig,str) and re.fullmatch('[A-Za-z0-9_-]{86}',sig),"Signaturkodierung ungueltig"
key=serialization.load_pem_public_key((work/'release-public.pem').read_bytes())
assert isinstance(key,Ed25519PublicKey)
canonical=json.dumps(m,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
key.verify(base64.urlsafe_b64decode(sig+'=='),b'ASK-ARM64-RELEASE-1\0'+canonical)
archive=work/m['artifact']
assert archive.stat().st_size==m['size'],"Archivgroesse falsch"
hash=hashlib.sha256()
with archive.open('rb') as f:
    for block in iter(lambda:f.read(1024*1024),b''):hash.update(block)
assert hash.hexdigest()==m['sha256'],"SHA256 falsch"
with tarfile.open(archive,'r:gz') as tf:
    names=set()
    for x in tf:
        q=pathlib.PurePosixPath(x.name)
        assert not q.is_absolute() and '..' not in q.parts and not (x.issym() or x.islnk() or x.isdev()) and (x.isfile() or x.isdir()),"Unsicherer Archiveintrag"
        assert q.parts and q.parts[0] in {'nuitka_entry.dist','BUILD-VERSION.txt'},"Fremder Archivpfad"
        assert x.name not in names,"Doppelter Archivpfad"
        names.add(x.name)
    assert 'BUILD-VERSION.txt' in names and 'nuitka_entry.dist/knx-alarmserver' in names,"Programmdateien fehlen"
    assert tf.extractfile('BUILD-VERSION.txt').read().decode().strip()==expected,"Build-Version falsch"
print("Ed25519-Signatur und SHA-256 erfolgreich geprueft:",expected)
PY
release="/opt/knx-alarmserver/releases/${tag#v}"
[[ ! -e $release ]] || { echo "Release-Verzeichnis bereits vorhanden." >&2; exit 1; }
install -d -m 0755 /opt/knx-alarmserver/releases
install -d -m 0755 "$release"
tar -xzf "$work/knx-alarmserver-arm64-nuitka.tar.gz" -C "$release" --no-same-owner --no-same-permissions
binary="$release/nuitka_entry.dist/knx-alarmserver"
chmod 0755 "$binary"
getent passwd knx-alarmserver >/dev/null || useradd --system --home-dir /var/lib/knx-alarmserver --shell /usr/sbin/nologin knx-alarmserver
install -d -m 0750 -o root -g knx-alarmserver /etc/knx-alarmserver
install -d -m 0700 -o knx-alarmserver -g knx-alarmserver /var/lib/knx-alarmserver /var/lib/knx-alarmserver/backups
cat > /etc/knx-alarmserver/config.toml <<'TOML'
[server]
host = "0.0.0.0"
port = 80
database = "/var/lib/knx-alarmserver/alarmserver.sqlite3"
alarms = "/etc/knx-alarmserver/alarms.csv"
retention_days = 365
[knx]
enabled = false
TOML
echo 'id;name;group_address;dpt;operator;threshold;hysteresis;field;area;priority;disabled' > /etc/knx-alarmserver/alarms.csv
chown root:knx-alarmserver /etc/knx-alarmserver/{config.toml,alarms.csv}
chmod 0640 /etc/knx-alarmserver/{config.toml,alarms.csv}
ln -s "$release" /opt/knx-alarmserver/current
runuser -u knx-alarmserver -- "$binary" -c /etc/knx-alarmserver/config.toml check
echo "Ersten Administrator anlegen:"
read -r -p "Admin-E-Mail-Adresse: " email
[[ -n $email ]] || { echo "E-Mail fehlt." >&2; exit 1; }
runuser -u knx-alarmserver -- "$binary" -c /etc/knx-alarmserver/config.toml user-add "$email" --role admin
cat > /etc/systemd/system/knx-alarmserver.service <<'UNIT'
[Unit]
Description=KNX Alarmserver (signed ARM64)
Wants=network-online.target
After=network-online.target
[Service]
Type=simple
User=knx-alarmserver
Group=knx-alarmserver
WorkingDirectory=/var/lib/knx-alarmserver
ExecStart=/opt/knx-alarmserver/current/nuitka_entry.dist/knx-alarmserver -c /etc/knx-alarmserver/config.toml serve
Restart=on-failure
RestartSec=10
UMask=0077
NoNewPrivileges=true
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/knx-alarmserver
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6 AF_NETLINK
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now knx-alarmserver
for i in $(seq 1 30); do
    if curl -fsS --max-time 2 http://127.0.0.1/health/live; then
        echo
        echo "Installation erfolgreich: http://$(hostname -I | awk '{print $1}')/"
        exit 0
    fi
    sleep 1
done
echo "Dienst antwortet nicht. journalctl -u knx-alarmserver -n 100" >&2
exit 1
