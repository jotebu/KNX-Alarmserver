"""Queue only a fixed systemd updater; never run privileged code in the web process."""
import os
import json
import threading
from pathlib import Path

ACTIVE = {'queued', 'fetching', 'installing'}


class DashboardUpdate:
    def __init__(self, request_path='/var/lib/knx-alarmserver/update-request',
                 status_path='/run/knx-alarmserver-update/status.json',
                 helper_path='/usr/local/libexec/knx-alarmserver-update.py',
                 unit_path='/etc/systemd/system/knx-alarmserver-update.path'):
        self.request_path = Path(request_path)
        self.status_path = Path(status_path)
        self.helper_path, self.unit_path = Path(helper_path), Path(unit_path)
        self.lock = threading.Lock()

    def status(self):
        available = self.helper_path.is_file() and self.unit_path.is_file()
        try:
            result = json.loads(self.status_path.read_text())
            if not isinstance(result, dict):
                raise ValueError('Invalid status')
        except (OSError, ValueError):
            result = {'state': 'idle'}
        if self.request_path.exists() or self.request_path.is_symlink():
            result = {'state': 'queued', 'message': 'Update angefordert; Start wird vorbereitet.'}
        return {**result, 'available': available}

    def start(self):
        with self.lock:
            status = self.status()
            if not status['available']:
                raise RuntimeError('Update-Dienst fehlt. Einmalig den aktuellen Installer per SSH ausfuehren.')
            if status.get('state') in ACTIVE:
                raise FileExistsError('Ein Update ist bereits angefordert oder aktiv')
            # No content or arguments are passed to the privileged service.
            fd = os.open(self.request_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            os.close(fd)
            return {'state': 'queued', 'available': True,
                    'message': 'Update angefordert; der Dienst kann kurzzeitig nicht erreichbar sein.'}
