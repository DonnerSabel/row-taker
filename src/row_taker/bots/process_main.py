from __future__ import annotations

import argparse
import random
import sys

from row_taker.clients.random_bot_client import RandomBotClient
from row_taker.protocol.framing import decode_server_message, encode_client_message


def main() -> int:
    parser = argparse.ArgumentParser(description='Run a row-taker bot process')
    parser.add_argument('--seed', type=int, default=None)
    args = parser.parse_args()

    bot = RandomBotClient(rng=random.Random(args.seed))
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer

    for line in stdin:
        message = decode_server_message(line)
        response = bot.handle_server_message(message)
        if response is None:
            raise RuntimeError(f'bot received unsupported server message: {type(message)!r}')
        stdout.write(encode_client_message(response))
        stdout.flush()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
