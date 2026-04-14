from __future__ import annotations

import argparse
import logging
import random
import sys

from row_taker.clients.random_bot_client import RandomBotClient
from row_taker.logging_utils import configure_logging
from row_taker.protocol.errors import ConnectionClosed, TransportError
from row_taker.protocol.messages import JoinLobby, SessionEnded
from row_taker.protocol.transport import ClientTransport


logger = logging.getLogger("row_taker.bot.process")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a row-taker bot process")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--log-level")
    parser.add_argument("--log-file")
    args = parser.parse_args()

    configure_logging(args.log_level, log_file=args.log_file)

    bot = RandomBotClient(rng=random.Random(args.seed))
    transport = ClientTransport.connect(args.host, args.port)
    try:
        transport.send(
            JoinLobby(
                display_name=args.display_name,
                requested_client_id=args.client_id,
            )
        )
        while True:
            try:
                message = transport.receive()
            except ConnectionClosed:
                logger.debug("bot transport closed by peer")
                return 0
            logger.debug("bot received server message: type=%s", type(message).__name__)
            if isinstance(message, SessionEnded):
                logger.debug("bot session ended received; exiting process")
                return 0
            response = bot.handle_server_message(message)
            if response is not None:
                logger.debug("bot sending client message: type=%s", type(response).__name__)
                transport.send(response)
    except TransportError as exc:
        print(f"Bot transport error: {exc}", file=sys.stderr)
        return 1
    finally:
        logger.debug("bot transport close start")
        transport.close()
        logger.debug("bot transport close complete")
        logger.debug("bot process main finished")


if __name__ == "__main__":
    raise SystemExit(main())
