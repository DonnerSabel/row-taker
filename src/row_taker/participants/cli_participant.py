from __future__ import annotations

from dataclasses import dataclass

from row_taker.cli.input_helpers import choose_card_cli, choose_row_cli_from_player_state
from row_taker.engine.commands import ChooseRowCommand, PlayCardCommand
from row_taker.engine.state import PlayerState


@dataclass(slots=True)
class CliParticipant:
    def on_choose_card_request(self, state: PlayerState) -> PlayCardCommand:
        return choose_card_cli(state)

    def on_choose_row_request(self, state: PlayerState) -> ChooseRowCommand:
        return choose_row_cli_from_player_state(state)
