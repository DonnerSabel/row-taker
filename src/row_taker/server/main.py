from __future__ import annotations

import argparse

from row_taker.server.network_server import run_network_server


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a row-taker server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    run_network_server(args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
