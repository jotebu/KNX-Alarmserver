"""Change explicit server listener settings while preserving unrelated TOML values."""
from pathlib import Path
import re
import tomllib


def configure_server(path, host=None, port=None):
    if port is not None and (type(port) is not int or not 1 <= port <= 65535):
        raise ValueError('Port muss zwischen 1 und 65535 liegen')
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
    changes = {}
    if host is not None:
        changes['host'] = host
    if port is not None:
        changes['port'] = port
    for key, value in changes.items():
        matches = [i for i in range(start + 1, end)
                   if re.match(r'\s*' + key + r'\s*=', lines[i])]
        if key in config['server'] and len(matches) != 1:
            raise ValueError(f'{key}-Zeile nicht eindeutig; bitte manuell setzen')
        encoded = f'"{value}"' if isinstance(value, str) else str(value)
        line = f'{key} = {encoded}\n'
        if matches:
            lines[matches[0]] = line
        else:
            if not lines[start].endswith('\n'):
                lines[start] += '\n'
            lines.insert(start + 1, line)
            end += 1
    updated = "".join(lines)
    expected = tomllib.loads(original)
    expected["server"].update(changes)
    if tomllib.loads(updated) != expected:
        raise ValueError("Unerwartete Konfigurationsaenderung")
    if updated != original:
        path.write_text(updated, encoding="utf-8")


def enable_lan(path):
    configure_server(path, host='0.0.0.0')


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    parser.add_argument('--lan', action='store_true')
    parser.add_argument('--port', type=int)
    args = parser.parse_args()
    # Preserve the original single-path invocation for external callers.
    host = '0.0.0.0' if args.lan or args.port is None else None
    configure_server(args.path, host=host, port=args.port)

