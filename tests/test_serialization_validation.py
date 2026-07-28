from __future__ import annotations

import json

import pytest

from row_taker.engine.game import setup_game
from row_taker.engine.game.state_mappers import public_state_from_dict, public_state_to_dict
from row_taker.engine.game.views import build_public_state
from row_taker.protocol.errors import MessageDecodeError
from row_taker.protocol.framing import decode_client_message, decode_server_message


def _public_state_data() -> dict[str, object]:
    state = build_public_state(setup_game(["Alice", "Bob"]))
    return public_state_to_dict(state)


def test_public_state_rejects_string_instead_of_integer() -> None:
    data = _public_state_data()
    data["round_no"] = "1"

    with pytest.raises(TypeError, match=r"public_state\.round_no must be an int"):
        public_state_from_dict(data)


def test_public_state_rejects_boolean_instead_of_integer() -> None:
    data = _public_state_data()
    data["trick_no"] = True

    with pytest.raises(TypeError, match=r"public_state\.trick_no must be an int"):
        public_state_from_dict(data)


def test_public_state_rejects_non_sequence_players_with_field_path() -> None:
    data = _public_state_data()
    data["players"] = {"not": "a list"}

    with pytest.raises(TypeError, match=r"public_state\.players must be a list"):
        public_state_from_dict(data)


def test_client_decode_reports_invalid_field_path() -> None:
    payload = json.dumps({"type": "clear_seat", "seat_index": "1"}).encode()

    with pytest.raises(MessageDecodeError, match=r"clear_seat\.seat_index must be an int"):
        decode_client_message(payload)


def test_server_decode_rejects_non_list_plays() -> None:
    payload = json.dumps(
        {"type": "cards_revealed", "plays": {"not": "a list"}, "revision": 1}
    ).encode()

    with pytest.raises(MessageDecodeError, match=r"cards_revealed\.plays must be a list"):
        decode_server_message(payload)


def test_server_decode_rejects_boolean_revision() -> None:
    payload = json.dumps({"type": "cards_revealed", "plays": [], "revision": True}).encode()

    with pytest.raises(MessageDecodeError, match=r"cards_revealed\.revision must be an int"):
        decode_server_message(payload)
