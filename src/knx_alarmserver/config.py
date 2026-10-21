"""Strict configuration and alarm matrix loading; no guessed group addresses."""

import csv
from dataclasses import dataclass
from pathlib import Path
import re
import tomllib

from .rules import threshold_from_text, validate_rule


@dataclass(frozen=True)
class Alarm:
    id: str
    name: str
    group_address: str
    dpt: str
    operator: str
    threshold: object
    hysteresis: float
    field: str
    area: str
    priority: str


def load_alarms(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        fields = set(Alarm.__dataclass_fields__)
        if not reader.fieldnames or set(reader.fieldnames) != fields:
            raise ValueError("CSV-Kopf erwartet: id;name;group_address;dpt;operator;threshold;hysteresis;field;area;priority")
        result, ids, addresses = [], set(), set()
        for line, row in enumerate(reader, 2):
            try:
                if None in row or any(v is None for v in row.values()):
                    raise ValueError("Spaltenanzahl stimmt nicht")
                row = {k: v.strip() for k, v in row.items()}
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", row["id"]):
                    raise ValueError("ungueltige ID")
                parts = row["group_address"].split("/")
                if len(parts) != 3 or any(not p.isdecimal() for p in parts):
                    raise ValueError("Gruppenadresse muss dreistufig sein")
                a, b, c = map(int, parts)
                if not (0 <= a <= 31 and 0 <= b <= 7 and 0 <= c <= 255):
                    raise ValueError("Gruppenadresse ausserhalb KNX-Bereich")
                row["group_address"] = f"{a}/{b}/{c}"
                if not re.fullmatch(r"[1-9][0-9]{0,2}(\.[0-9]{3})?", row["dpt"]):
                    raise ValueError("DPT als Hauptnummer oder vollstaendig, z.B. 9.001")
                row["threshold"] = threshold_from_text(row["threshold"])
                row["hysteresis"] = float(row["hysteresis"] or "0")
                if not row["name"] or len(row["name"]) > 200:
                    raise ValueError("Name fehlt oder ist zu lang")
                if row["priority"] not in {"info", "warning", "critical"}:
                    raise ValueError("priority: info, warning oder critical")
                if row["id"] in ids or row["group_address"] in addresses:
                    raise ValueError("doppelte ID oder Gruppenadresse")
                ids.add(row["id"])
                addresses.add(row["group_address"])
                alarm = Alarm(**row)
                validate_rule(alarm)
                result.append(alarm)
            except (TypeError, ValueError) as error:
                raise ValueError(f"CSV Zeile {line}: {error}") from error
    return result


def load_config(path):
    path = Path(path).resolve()
    with path.open("rb") as handle:
        config = tomllib.load(handle)
    allowed = {"server", "knx"}
    if set(config) - allowed:
        raise ValueError("Unbekannter Konfigurationsabschnitt")
    server = config.setdefault("server", {})
    if set(server) - {"host", "port", "database", "alarms", "retention_days"}:
        raise ValueError("Unbekannte server-Option")
    for key, default in (("database", "alarmserver.sqlite3"), ("alarms", "alarms.csv")):
        server[key] = str((path.parent / server.get(key, default)).resolve())
    server.setdefault("host", "127.0.0.1")
    server.setdefault("port", 8080)
    server.setdefault("retention_days", 365)
    if not 1 <= server["port"] <= 65535 or not 1 <= server["retention_days"] <= 3650:
        raise ValueError("Port oder Aufbewahrungsdauer ungueltig")
    knx = config.setdefault("knx", {})
    if set(knx) - {"enabled", "connections"}:
        raise ValueError("Unbekannte knx-Option")
    knx.setdefault("enabled", False)
    connections = knx.setdefault("connections", [])
    names = set()
    for connection in connections:
        if set(connection) - {"name", "type", "gateway_ip", "gateway_port", "local_ip", "individual_address", "multicast_group"}:
            raise ValueError("Unbekannte KNX-Verbindungsoption")
        name = connection.get("name", "")
        if not name or name in names:
            raise ValueError("KNX-Verbindungsnamen muessen eindeutig sein")
        names.add(name)
        kind = connection.get("type", "tunneling")
        if kind not in {"tunneling", "routing"}:
            raise ValueError("KNX-Typ muss tunneling oder routing sein")
        if kind == "tunneling" and not connection.get("gateway_ip"):
            raise ValueError("gateway_ip fehlt")
        if kind == "routing" and not connection.get("individual_address"):
            raise ValueError("Routing benoetigt eine in ETS abgestimmte individual_address")
    if knx["enabled"] and not connections:
        raise ValueError("KNX aktiviert, aber keine Verbindung konfiguriert")
    return config
