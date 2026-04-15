from __future__ import annotations

import argparse

from row_taker.gui_demo.app import GuiDemoApp
from row_taker.gui_demo.live_client import LiveGuiClient
from row_taker.logging_utils import configure_logging
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
    parser = argparse.ArgumentParser(description="Run the row-taker pygame demo client")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--name")
    parser.add_argument("--log-level")
    parser.add_argument("--log-file")
    args, _unknown = parser.parse_known_args()

    configure_logging(args.log_level, log_file=args.log_file)

    wants_live = not args.demo and any(value is not None for value in (args.host, args.port, args.name))
    if not wants_live:
        GuiDemoApp().run()
        return

    host = args.host or _prompt_host()
    port = args.port if args.port is not None else _prompt_port()
    display_name = args.name or _prompt_name()

    transport = ClientTransport.connect(host, port)
    live_client = LiveGuiClient(transport, display_name=display_name)
    GuiDemoApp(live_client=live_client).run()


def run() -> int:
    try:
        main()
        return 0
    except KeyboardInterrupt:
        return 0
