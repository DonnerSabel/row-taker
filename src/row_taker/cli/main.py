from __future__ import annotations

from row_taker.cli.client_session import ClientSession, print_final_result
from row_taker.cli.terminal import clear_screen
from row_taker.clients.cli_client import CliClient
from row_taker.protocol.messages import JoinLobby
from row_taker.protocol.transport import ClientTransport
from row_taker.server.network_server import start_background_network_server


def _prompt_mode() -> str:
    while True:
        value = input("Modus [h=host, j=join] > ").strip().lower()
        if value in {"h", "j"}:
            return value
        print("Bitte h oder j eingeben.")


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


def _prompt_seat_count(default: int = 4) -> int:
    while True:
        value = input(f"Anzahl der Plätze (2-6) [{default}] > ").strip()
        if not value:
            return default
        if value.isdigit():
            count = int(value)
            if 2 <= count <= 6:
                return count
        print("Bitte eine Zahl zwischen 2 und 6 eingeben.")


def main() -> None:
    clear_screen()
    print("Row-Taker – CLI")
    print()

    mode = _prompt_mode()
    if mode == "h":
        seat_count = _prompt_seat_count()
        handle = start_background_network_server(seat_count=seat_count)
        host = handle.host
        port = handle.port
        print(f"Lokaler Server läuft auf {host}:{port}")
    else:
        host = _prompt_host()
        port = _prompt_port()

    display_name = _prompt_name()
    transport = ClientTransport.connect(host, port)
    transport.send(JoinLobby(display_name=display_name))

    session = ClientSession(transport=transport, ui_client=CliClient())
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
