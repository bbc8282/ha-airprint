#!/usr/bin/env python3
"""Route CUPS job diagnostics to the app log without changing print settings."""
import argparse
from pathlib import Path

LOG_LEVELS = ("warn", "info", "debug")


def update_directives(content, values):
    pending = {key.lower(): (key, value) for key, value in values.items()}
    managed = set(pending)
    lines = []
    for line in content.splitlines():
        fields = line.split()
        key = fields[0].lower() if fields else ""
        if key in managed:
            if key in pending:
                name, value = pending.pop(key)
                lines.append(f"{name} {value}")
        else:
            lines.append(line)
    lines.extend(f"{key} {value}" for key, value in pending.values())
    return "\n".join(lines) + "\n"


def configure(server_path, files_path, log_level):
    if log_level not in LOG_LEVELS:
        raise ValueError("Expected warn, info or debug")
    server_path, files_path = Path(server_path), Path(files_path)
    server = update_directives(server_path.read_text(), {
        "LogLevel": log_level, "AccessLogLevel": "actions",
    })
    files = update_directives(files_path.read_text(), {
        "ErrorLog": "stderr", "AccessLog": "stderr",
    })
    server_path.write_text(server)
    files_path.write_text(files)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-level", choices=LOG_LEVELS, default="info")
    parser.add_argument("--server-config", default="/etc/cups/cupsd.conf")
    parser.add_argument("--files-config", default="/etc/cups/cups-files.conf")
    args = parser.parse_args()
    configure(args.server_config, args.files_config, args.log_level)
