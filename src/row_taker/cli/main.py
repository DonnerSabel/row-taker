from __future__ import annotations

from row_taker.cli.client_session import ClientSession, SocketTransport, print_final_result
from row_taker.cli.create_match_config import create_single_human_match_config
from row_taker.cli.terminal import clear_screen
from row_taker.clients.cli_client import CliClient
from row_taker.protocol.messages import ConfigureLobby, StartGame
from row_taker.server.network_server import start_background_network_server


def _prompt_mode() -> str:
    while True:
        value = input("Modus [h=host, j=join] > ").strip().lower()
        if value in {"h", "j"}:
            return value
        print("Bitte h oder j eingeben.")


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
    clear_screen()
    print("Row-Taker – CLI")
    print()

    mode = _prompt_mode()
    if mode == "h":
        handle = start_background_network_server()
        host = handle.host
        port = handle.port
        print(f"Lokaler Server läuft auf {host}:{port}")
    else:
        host = _prompt_host()
        port = _prompt_port()

    match_config = create_single_human_match_config()
    transport = SocketTransport.connect(host, port)
    transport.send(ConfigureLobby(match_config=match_config))
    transport.send(StartGame())

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
