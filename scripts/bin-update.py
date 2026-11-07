#!/usr/bin/env python3
"""Signed ARM64 updater for KNX Alarmserver. Installed root-owned, invoked by systemd."""
import base64
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime, timezone
import tomllib
from urllib.request import Request, urlopen
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path("/opt/knx-alarmserver")
CURRENT = ROOT / "current"
DATA = Path("/var/lib/knx-alarmserver")
REQUEST = DATA / "update-request"
STATUS = Path("/run/knx-alarmserver-update/status.json")
LOCK = Path("/run/lock/knx-alarmserver-binupdate.lock")
CONFIG = Path("/etc/knx-alarmserver/config.toml")
API = "https://api.github.com/repos/jotebu/KNX-Alarmserver/releases/latest"
ARCHIVE = "knx-alarmserver-arm64-nuitka.tar.gz"
PUBKEY = b"""-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAL/KW5R+8mYsDxOlVJhXY6Wz56Ijvm6lU6DmK8gXUYD8=
-----END PUBLIC KEY-----
"""
ACTIVE = {"fetching", "installing", "verifying"}
USER_AGENT = "KNX-Alarmserver-Updater/1.0"

def status(state, message, **extra):
    STATUS.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
    obj = {"state": state, "message": message,
           "updated_at": datetime.now(timezone.utc).isoformat(), **extra}
    fd, name = tempfile.mkstemp(prefix=".status-", dir=STATUS.parent)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(name, 0o644)
        os.replace(name, STATUS)
    finally:
        Path(name).unlink(missing_ok=True)

def fetch(url, dest, max_size):
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=40) as response, open(dest, "wb") as f:
        if response.url.split(":", 1)[0] != "https":
            raise ValueError("Only HTTPS downloads allowed")
        size = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > max_size:
                raise ValueError("Download exceeds size limit")
            f.write(chunk)

def verified_release(work, current_version):
    release_data = work / "latest.json"
    fetch(API, release_data, 256 * 1024)
    obj = json.loads(release_data.read_text())
    tag = obj.get("tag_name", "")
    if not isinstance(tag, str) or not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag):
        raise ValueError("Invalid release tag")
    target = tag[1:]
    if tuple(map(int, target.split("."))) <= tuple(map(int, current_version.split("."))):
        return None, target
    assets = {a.get("name"): a.get("browser_download_url") for a in obj.get("assets", [])
              if isinstance(a, dict)}
    for filename in ("arm64-release.json", ARCHIVE):
        url = assets.get(filename)
        expected_prefix = f"https://github.com/jotebu/KNX-Alarmserver/releases/download/{tag}/"
        if not isinstance(url, str) or url != expected_prefix + filename:
            raise ValueError("Unexpected release asset URL")
    fetch(assets["arm64-release.json"], work / "arm64-release.json", 8192)
    envelope = json.loads((work / "arm64-release.json").read_text())
    if not isinstance(envelope, dict) or set(envelope) != {"manifest", "signature"}:
        raise ValueError("Invalid signature envelope")
    manifest = envelope["manifest"]
    if not isinstance(manifest, dict) or set(manifest) != {"format", "version", "platform", "artifact", "size", "sha256"}:
        raise ValueError("Invalid manifest fields")
    if (manifest["format"], manifest["version"], manifest["platform"], manifest["artifact"]) != (
        "ASK-ARM64-RELEASE-1", target, "linux-aarch64", ARCHIVE):
        raise ValueError("Manifest does not match release")
    n = manifest["size"]
    sha = manifest["sha256"]
    if type(n) is not int or not 0 < n <= 512 * 1024 * 1024:
        raise ValueError("Invalid release size")
    if not isinstance(sha, str) or not re.fullmatch("[0-9a-f]{64}", sha):
        raise ValueError("Invalid checksum")
    signature = envelope["signature"]
    if not isinstance(signature, str) or not re.fullmatch("[A-Za-z0-9_-]{86}", signature):
        raise ValueError("Invalid signature encoding")
    pubkey = serialization.load_pem_public_key(PUBKEY)
    assert isinstance(pubkey, Ed25519PublicKey)
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    pubkey.verify(base64.urlsafe_b64decode(signature + "=="), b"ASK-ARM64-RELEASE-1\0" + canonical)
    archive = work / ARCHIVE
    fetch(assets[ARCHIVE], archive, n)
    if archive.stat().st_size != n:
        raise ValueError("Archive size mismatch")
    digest = hashlib.sha256()
    with archive.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != sha:
        raise ValueError("Archive checksum mismatch")
    with tarfile.open(archive, "r:gz") as tf:
        seen = set()
        for member in tf:
            p = PurePosixPath(member.name)
            if (p.is_absolute() or ".." in p.parts or not p.parts
                or p.parts[0] not in {"BUILD-VERSION.txt", "nuitka_entry.dist"}
                or not (member.isfile() or member.isdir())
                or member.name in seen):
                raise ValueError("Unsafe archive entry")
            seen.add(member.name)
        if "BUILD-VERSION.txt" not in seen or "nuitka_entry.dist/knx-alarmserver" not in seen:
            raise ValueError("Missing executable or version")
        if tf.extractfile("BUILD-VERSION.txt").read().decode().strip() != target:
            raise ValueError("Embedded version mismatch")
    return archive, target

def current_version():
    version_file = CURRENT / "BUILD-VERSION.txt"
    version = version_file.read_text().strip()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("Invalid installed version")
    return version

def db_backup():
    with CONFIG.open("rb") as f:
        config = tomllib.load(f)
    db = Path(config["server"]["database"])
    if not db.is_file():
        raise RuntimeError("Database missing, refusing update")
    targetdir = DATA / "backups"
    targetdir.mkdir(mode=0o700, parents=True, exist_ok=True)
    target = targetdir / ("before-update-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + str(os.getpid()) + ".sqlite3")
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as source, sqlite3.connect(target) as dst:
        source.backup(dst)
        row = dst.execute("PRAGMA integrity_check").fetchone()
        if row is None or row[0] != "ok":
            raise RuntimeError("Backup integrity check failed")
    os.chmod(target, 0o600)
    return str(target)

def swap(target):
    temp = ROOT / (".current-" + str(os.getpid()))
    temp.symlink_to(target)
    os.replace(temp, CURRENT)

def restart_and_verify(version):
    subprocess.run(["systemctl", "restart", "knx-alarmserver.service"], check=True, timeout=60)
    with CONFIG.open("rb") as f:
        config = tomllib.load(f)["server"]
    port = config["port"]
    import urllib.request
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health/live", timeout=2) as response:
                state = json.load(response)
                if state.get("status") == "ok" and state.get("version") == version:
                    return
        except (OSError, ValueError):
            pass
        time.sleep(1)
    raise RuntimeError("Health check failed after restart")

def run():
    if os.geteuid() != 0:
        raise RuntimeError("Updater must run as root")
    with LOCK.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not (REQUEST.exists() or REQUEST.is_symlink()):
            return
        REQUEST.unlink()
        old_target = CURRENT.resolve(strict=True)
        old_version = current_version()
        switched = False
        stage = None
        try:
            status("fetching", "Signiertes GitHub-Release wird geprüft.", previous_version=old_version)
            with tempfile.TemporaryDirectory(prefix="knx-arm64-update-") as d:
                archive, version = verified_release(Path(d), old_version)
                if archive is None:
                    status("current", "Keine neuere Version verfügbar.", previous_version=old_version, target_version=version)
                    return
                stage = ROOT / "releases" / version
                if stage.exists():
                    raise RuntimeError("Target release directory already exists")
                status("installing", "Datenbank sichern und Release installieren.", previous_version=old_version, target_version=version)
                backup = db_backup()
                stage.mkdir(mode=0o755, parents=True)
                with tarfile.open(archive, "r:gz") as tf:
                    tf.extractall(stage, filter="data")
                binary = stage / "nuitka_entry.dist" / "knx-alarmserver"
                binary.chmod(0o755)
                # Keep a rollback target until the health check passes.
                swap(stage)
                switched = True
                restart_and_verify(version)
                (ROOT / "previous").unlink(missing_ok=True)
                (ROOT / "previous").symlink_to(old_target)
                status("success", "Update erfolgreich installiert.", previous_version=old_version,
                       target_version=version, backup=backup)
        except Exception as e:
            if switched:
                try:
                    swap(old_target)
                    restart_and_verify(old_version)
                    status("failed", "Update fehlgeschlagen; vorherige Version wiederhergestellt.",
                           previous_version=old_version, error=str(e))
                except Exception as rollback_error:
                    status("failed", "Update und Rückwechsel fehlgeschlagen; manueller Eingriff erforderlich.",
                           previous_version=old_version, error=str(e), rollback_error=str(rollback_error))
            else:
                status("failed", "Update fehlgeschlagen; bisheriger Dienst unverändert.", error=str(e))
            raise

def finish():
    try:
        obj = json.loads(STATUS.read_text())
    except (OSError, ValueError):
        return
    if obj.get("state") in ACTIVE:
        status("failed", "Update unerwartet unterbrochen. Dienstprotokoll prüfen.")

if __name__ == "__main__":
    if sys.argv[1:] == ["--finish"]:
        finish()
    elif not sys.argv[1:]:
        run()
    else:
        raise SystemExit("Unexpected arguments")
