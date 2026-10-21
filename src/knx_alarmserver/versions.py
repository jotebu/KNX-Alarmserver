"""Bounded, cached public version checks; no credentials or building data sent."""
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
import threading
import time
import tomllib
import urllib.request

from . import __version__

BASE = 'https://raw.githubusercontent.com/jotebu/KNX-Alarmserver/main/'


def version_number(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,8}\.[0-9]{1,8}\.[0-9]{1,8}', value):
        raise ValueError('Ungueltige Versionsnummer')
    return tuple(map(int, value.split('.')))


def fetch_text(filename):
    if filename not in {'pyproject.toml', 'CHANGELOG.md'}:
        raise ValueError('Unsupported version resource')
    request = urllib.request.Request(BASE + filename, headers={'User-Agent':'KNX-Alarmserver-VersionCheck'})
    with urllib.request.urlopen(request, timeout=3) as response:
        raw = response.read(262145)
    if len(raw) > 262144:
        raise ValueError('Version resource too large')
    return raw.decode('utf-8')


class VersionChecker:
    def __init__(self, history_path=None):
        self.history_path = Path(history_path) if history_path is not None else None
        self.lock = threading.RLock()
        self.cached = None
        self.expires = 0
        self.history_cached = None
        self.history_expires = 0

    def check(self):
        with self.lock:
            if self.cached is not None and time.monotonic() < self.expires:
                return dict(self.cached)
            checked = datetime.now(timezone.utc).isoformat()
            try:
                latest = tomllib.loads(fetch_text('pyproject.toml'))['project']['version']
                update = version_number(latest) > version_number(__version__)
                result = {'current_version':__version__, 'latest_version':latest,
                          'update_available':update, 'check_ok':True, 'checked_at':checked}
                ttl = 300
            except (OSError, ValueError, KeyError, TypeError):
                result = {'current_version':__version__, 'latest_version':None,
                          'update_available':False, 'check_ok':False, 'checked_at':checked}
                ttl = 30
            self.cached, self.expires = result, time.monotonic() + ttl
            return dict(result)

    def local_history(self):
        candidates = [self.history_path] if self.history_path else [
            Path(sys.prefix).parent/'source'/'CHANGELOG.md',
            Path(__file__).resolve().parents[2]/'CHANGELOG.md']
        for path in candidates:
            try:
                return path.read_text(encoding='utf-8')[:262144]
            except OSError:
                continue
        return 'Keine lokale Versionshistorie vorhanden.'

    def history(self):
        result = self.check()
        with self.lock:
            if self.history_cached is None or time.monotonic() >= self.history_expires:
                try:
                    self.history_cached = {'changelog':fetch_text('CHANGELOG.md'), 'history_source':'github'}
                    self.history_expires = time.monotonic()+300
                except (OSError, ValueError):
                    self.history_cached = {'changelog':self.local_history(), 'history_source':'local'}
                    self.history_expires = time.monotonic()+30
            return {**result, **self.history_cached}
