#!/usr/bin/env python3
"""Root-owned, fixed-repository update worker, invoked only by systemd."""
import fcntl
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
import tomllib

REQUEST = Path('/var/lib/knx-alarmserver/update-request')
STATUS = Path('/run/knx-alarmserver-update/status.json')
LOCK = Path('/run/lock/knx-alarmserver-dashboard-update.lock')
CURRENT = Path('/opt/knx-alarmserver/current/source/pyproject.toml')
REPOSITORY = 'https://github.com/jotebu/KNX-Alarmserver.git'
ENV = {'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'HOME': '/root',
       'DEBIAN_FRONTEND': 'noninteractive', 'GIT_TERMINAL_PROMPT': '0',
       'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'}


def write_status(state, message, **extra):
    STATUS.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    payload = {'state': state, 'message': message,
               'updated_at': datetime.now(timezone.utc).isoformat(), **extra}
    fd, path = tempfile.mkstemp(prefix='.status-', dir=STATUS.parent)
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(payload, handle, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(path, 0o644)
        os.replace(path, STATUS)
    finally:
        Path(path).unlink(missing_ok=True)


def read_version(path):
    with Path(path).open('rb') as handle:
        value = tomllib.load(handle)['project']['version']
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,8}\.[0-9]{1,8}\.[0-9]{1,8}', value):
        raise ValueError('Invalid version')
    return value


def finish():
    try:
        state = json.loads(STATUS.read_text())
    except (OSError, ValueError):
        return
    if state.get('state') in {'fetching', 'installing'}:
        write_status('failed', 'Update unterbrochen. Dienstprotokoll pruefen: journalctl -u knx-alarmserver-update')


def run():
    if os.geteuid() != 0:
        raise RuntimeError('Updater requires systemd root service')
    with LOCK.open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Ignore request bytes and unlink a possible symlink without following it.
        if not REQUEST.exists() and not REQUEST.is_symlink():
            return
        write_status('fetching', 'Aktuellen Stand von GitHub laden …')
        REQUEST.unlink()
        work = None
        try:
            previous = read_version(CURRENT)
            work = Path(tempfile.mkdtemp(prefix='knx-dashboard-update-'))
            source = work / 'source'
            subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', 'clone', '--depth', '1',
                            '--branch', 'main', REPOSITORY, str(source)],
                           check=True, env=ENV, timeout=180)
            target = read_version(source / 'pyproject.toml')
            if tuple(map(int,target.split('.'))) <= tuple(map(int,previous.split('.'))):
                write_status('current', 'Keine neuere Version verfuegbar.', previous_version=previous, target_version=target)
                return
            commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], env=ENV, text=True).strip()
            write_status('installing', 'Installation läuft. Der Webdienst wird danach neu gestartet.',
                         previous_version=previous, target_version=target, commit=commit)
            # No user-supplied URL, branch, command, port or filename is accepted.
            subprocess.run(['/bin/bash', str(source / 'scripts/install.sh')],
                           check=True, env=ENV, stdin=subprocess.DEVNULL, timeout=1500)
            actual = read_version(CURRENT)
            if actual != target:
                raise RuntimeError('Installed version differs from target')
            write_status('success', 'Update erfolgreich abgeschlossen.',
                         previous_version=previous, target_version=actual, commit=commit)
        except Exception:
            write_status('failed', 'Update fehlgeschlagen. Dienstprotokoll pruefen: journalctl -u knx-alarmserver-update')
            raise
        finally:
            if work is not None:
                shutil.rmtree(work)


if __name__ == '__main__':
    if sys.argv[1:] == ['--finish']:
        finish()
    elif len(sys.argv) == 1:
        run()
    else:
        raise SystemExit('No update arguments accepted')
