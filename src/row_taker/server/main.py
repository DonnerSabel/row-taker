from __future__ import annotations

import argparse
import socket
from collections.abc import Iterable

from row_taker.logging_utils import configure_logging
from row_taker.server.network_server import run_network_server


def _discover_local_ipv4_addresses() -> list[str]:
    addresses: set[str] = {"127.0.0.1"}
    hostname = socket.gethostname()
    try:
        infos = socket.getaddrinfo(hostname, None, family=socket.AF_INET, type=socket.SOCK_STREAM)
    except OSError:
        infos = []
    for family, _socktype, _proto, _canonname, sockaddr in infos:
        if family == socket.AF_INET and sockaddr:
            host = str(sockaddr[0])
            if host != "127.0.0.1":
                addresses.add(host)

    for target in ("8.8.8.8", "1.1.1.1"):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect((target, 80))
                local_host = sock.getsockname()[0]
                if local_host and local_host != "127.0.0.1":
                    addresses.add(local_host)
        except OSError:
            continue

    return sorted(
        addresses,
        key=lambda value: (value != "127.0.0.1", tuple(int(part) for part in value.split("."))),
    )


def _prompt_choice(options: Iterable[str], label: str) -> str:
    values = list(options)
    if not values:
        raise ValueError("no options available")
    while True:
        print(label)
        for index, value in enumerate(values, start=1):
            print(f"  {index}) {value}")
        selection = input("Auswahl > ").strip()
        if selection.isdigit():
            chosen = int(selection)
            if 1 <= chosen <= len(values):
                return values[chosen - 1]
        print("Bitte eine gültige Nummer auswählen.")


def _prompt_port(default: int = 8765) -> int:
    while True:
        raw = input(f"Port [{default}] > ").strip()
        if not raw:
            return default
        if raw.isdigit():
            port = int(raw)
            if 1 <= port <= 65535:
                return port
        print("Bitte einen gültigen TCP-Port eingeben.")


def _prompt_seat_count(default: int = 4) -> int:
    while True:
        raw = input(f"Anzahl der Plätze (2-6) [{default}] > ").strip()
        if not raw:
            return default
        if raw.isdigit():
            count = int(raw)
            if 2 <= count <= 6:
                return count
        print("Bitte eine Zahl zwischen 2 und 6 eingeben.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a row-taker server")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--seat-count", type=int)
    parser.add_argument("--log-level")
    parser.add_argument("--log-file")
    args = parser.parse_args()

    configure_logging(args.log_level, log_file=args.log_file)

    host = args.host or _prompt_choice(
        _discover_local_ipv4_addresses(),
        "Server-IP auswählen:",
    )
    port = args.port if args.port is not None else _prompt_port()
    seat_count = args.seat_count if args.seat_count is not None else _prompt_seat_count()
    run_network_server(
        host,
        port,
        seat_count=seat_count,
        log_level=args.log_level,
        log_file=args.log_file,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
