from __future__ import annotations

import argparse

from row_taker.cli.client_session import ClientSession, print_final_result
from row_taker.cli.terminal import clear_screen
from row_taker.logging_utils import configure_logging
from row_taker.protocol.messages import JoinLobby
from row_taker.protocol.transport import ClientTransport


def _prompt_name(default: str = "Spieler") -> str:
    value = input(f"Anzeigename [{default}] > ").strip()
    return value or default


def _prompt_host(default: str = "127.0.0.1") -> str:
    value = input(f"Server-IP [{default}] > ").strip()
    return value or default


def _prompt_port(default: int = 8765) -> int:
    while True:
        value = input(f"Port [{default}] > ").strip()
        if not value:
            return default
        if value.isdigit():
            port = int(value)
            if 1 <= port <= 65535:
                return port
        print("Bitte einen gültigen TCP-Port eingeben.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a row-taker CLI client")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--name")
    parser.add_argument("--log-level")
    args, _unknown = parser.parse_known_args()

    configure_logging(args.log_level)

    clear_screen()
    print("Row-Taker – CLI")
    print()

    host = args.host or _prompt_host()
    port = args.port if args.port is not None else _prompt_port()
    display_name = args.name or _prompt_name()

    transport = ClientTransport.connect(host, port)
    transport.send(JoinLobby(display_name=display_name))

    session = ClientSession(transport=transport)
    final_state = session.run()
    print_final_result(final_state)


def run() -> int:
    try:
        main()
        return 0
    except KeyboardInterrupt:
        clear_screen()
        print("Abbruch mit Strg+C!")
        return 0
