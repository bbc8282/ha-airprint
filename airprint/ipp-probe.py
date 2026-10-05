#!/usr/bin/env python3
"""Read-only IPP reachability probe. Never sends Print-Job or touches port 9100."""
import http.client
import struct
import sys
from urllib.parse import urlsplit


def endpoint(uri):
    value = urlsplit(uri)
    if value.scheme not in ("ipp", "ipps", "http", "https") or not value.hostname:
        raise ValueError("Expected an IPP or HTTP printer URI")
    if value.username or value.password or value.fragment:
        raise ValueError("Credentials/fragments in printer URIs are not supported")
    secure = value.scheme in ("ipps", "https")
    defaults = {"ipp": 631, "ipps": 631, "http": 80, "https": 443}
    port = value.port or defaults[value.scheme]
    path = value.path or "/"
    if value.query:
        path += "?" + value.query
    return value.hostname, port, secure, path


def attribute(tag, name, value):
    name, value = name.encode("utf-8"), value.encode("utf-8")
    return bytes([tag]) + struct.pack(">H", len(name)) + name + struct.pack(">H", len(value)) + value


def request_body(uri):
    # IPP 1.1, Get-Printer-Attributes, request-id 1.
    return (struct.pack(">BBHI", 1, 1, 0x000B, 1) + b"\x01"
            + attribute(0x47, "attributes-charset", "utf-8")
            + attribute(0x48, "attributes-natural-language", "en")
            + attribute(0x45, "printer-uri", uri)
            + attribute(0x44, "requested-attributes", "printer-state") + b"\x03")


def check(uri):
    host, port, secure, path = endpoint(uri)
    connection_type = http.client.HTTPSConnection if secure else http.client.HTTPConnection
    connection = connection_type(host, port, timeout=3)
    try:
        connection.request("POST", path, body=request_body(uri),
                           headers={"Content-Type": "application/ipp"})
        response = connection.getresponse()
        body = response.read(65536)
        if response.status != 200 or response.getheader("Content-Type", "").split(";", 1)[0].strip().lower() != "application/ipp":
            return False
        if len(body) < 9:
            return False
        major, minor, status, request_id = struct.unpack(">BBHI", body[:8])
        # Success status range; a plain HTTP page or rejected queue is not online.
        return major in (1, 2) and request_id == 1 and status < 0x0100 and body[-1:] == b"\x03"
    finally:
        connection.close()


if __name__ == "__main__":
    try:
        command, uri = sys.argv[1:]
        if command == "resolve":
            host, port, _, _ = endpoint(uri)
            print(f"{host}\t{port}")
        elif command == "check":
            sys.exit(0 if check(uri) else 1)
        else:
            raise ValueError("Unknown command")
    except (ValueError, OSError, http.client.HTTPException) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
