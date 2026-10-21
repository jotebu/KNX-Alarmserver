"""Enable direct IPv4 LAN access while preserving other TOML settings."""
from pathlib import Path
import re
import sys
import tomllib


def enable_lan(path):
    path = Path(path)
    original = path.read_text(encoding="utf-8")
    config = tomllib.loads(original)
    if not isinstance(config.get("server"), dict):
        raise ValueError("Abschnitt [server] fehlt")
    lines = original.splitlines(keepends=True)
    start = next(i for i, line in enumerate(lines)
                 if re.fullmatch(r"\s*\[server\]\s*(?:#.*)?", line.rstrip("\r\n")))
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].lstrip().startswith("[")), len(lines))
    hosts = [i for i in range(start + 1, end)
             if re.match(r"\s*host\s*=", lines[i])]
    if "host" in config["server"] and len(hosts) != 1:
        raise ValueError("host-Zeile nicht eindeutig; bitte manuell setzen")
    if hosts:
        lines[hosts[0]] = 'host = "0.0.0.0" # Direkter Zugriff im LAN\n'
    else:
        if not lines[start].endswith("\n"):
            lines[start] += "\n"
        lines.insert(start + 1, 'host = "0.0.0.0" # Direkter Zugriff im LAN\n')
    updated = "".join(lines)
    expected = tomllib.loads(original)
    expected["server"]["host"] = "0.0.0.0"
    if tomllib.loads(updated) != expected:
        raise ValueError("Unerwartete Konfigurationsaenderung")
    if updated != original:
        path.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    enable_lan(sys.argv[1])
