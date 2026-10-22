"""CLI for configuration checks, accounts, SQLite backups and service startup."""

import argparse
import getpass
import logging
from pathlib import Path

from .config import load_config, load_configured_alarms
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
    account.add_argument("--role", choices=("admin", "user", "viewer"))
    account.add_argument("--first-name")
    account.add_argument("--last-name")
    profile = commands.add_parser("user-profile")
    profile.add_argument("username")
    profile.add_argument("first_name")
    profile.add_argument("last_name")
    backup = commands.add_parser("backup")
    backup.add_argument("destination")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = load_config(args.config)
    alarms = load_configured_alarms(config)
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
            existing = store.account(args.username)
            first_name = args.first_name
            last_name = args.last_name
            if not existing:
                first_name = first_name if first_name is not None else input("Vorname: ")
                last_name = last_name if last_name is not None else input("Nachname: ")
                store._validate_profile(args.username, first_name, last_name)
            elif first_name is not None or last_name is not None:
                store._validate_names(first_name, last_name)
            password = getpass.getpass("Passwort (mindestens 12 Zeichen): ")
            if password != getpass.getpass("Passwort wiederholen: "):
                raise ValueError("Passwoerter stimmen nicht ueberein")
            with store.transaction():
                store.set_password(args.username, password, args.role)
                if first_name is not None:
                    store.set_profile(args.username, first_name, last_name)
            print("Benutzer gespeichert.")
        elif args.command == "user-profile":
            store.set_profile(args.username, args.first_name, args.last_name)
            print("Vor- und Nachname gespeichert.")
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

