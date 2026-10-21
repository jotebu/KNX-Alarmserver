"""CLI for configuration checks, accounts, SQLite backups and service startup."""

import argparse
import getpass
import logging
from pathlib import Path

from .config import load_alarms, load_config
from .store import Store


def main():
    parser = argparse.ArgumentParser(description="KNX Alarmserver")
    parser.add_argument("-c", "--config", default="/etc/knx-alarmserver/config.toml")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("serve")
    commands.add_parser("check")
    commands.add_parser("dpt-list")
    account = commands.add_parser("user-add")
    account.add_argument("username")
    backup = commands.add_parser("backup")
    backup.add_argument("destination")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = load_config(args.config)
    alarms = load_alarms(config["server"]["alarms"])
    from .dpt import catalog, transcoder
    for alarm in alarms:
        transcoder(alarm.dpt)
    if args.command == "dpt-list":
        import json
        print(json.dumps(catalog(), ensure_ascii=False, indent=2))
        return
    if args.command == "check":
        print(f"Konfiguration gueltig. Alarme: {len(alarms)}, KNX aktiviert: {config['knx']['enabled']}")
        return
    database = Path(config["server"]["database"])
    database.parent.mkdir(parents=True, exist_ok=True)
    store = Store(database, alarms, config["server"]["retention_days"])
    try:
        if args.command == "user-add":
            password = getpass.getpass("Passwort (mindestens 12 Zeichen): ")
            if password != getpass.getpass("Passwort wiederholen: "):
                raise ValueError("Passwoerter stimmen nicht ueberein")
            store.set_password(args.username, password)
            print("Benutzer gespeichert.")
        elif args.command == "backup":
            if Path(args.destination).exists():
                raise ValueError("Backup-Ziel existiert bereits")
            store.backup(args.destination)
            print("Konsistentes SQLite-Backup erstellt. config.toml und alarms.csv separat sichern.")
        else:
            import uvicorn
            from .web import create_app
            uvicorn.run(create_app(config, store), host=config["server"]["host"],
                        port=config["server"]["port"], workers=1, proxy_headers=False)
    finally:
        store.close()


if __name__ == "__main__":
    main()
