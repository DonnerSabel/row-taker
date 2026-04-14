from __future__ import annotations

import random
from dataclasses import dataclass, field

from row_taker.cli.state_models import has_pending_presentation, initial_cli_state
from row_taker.client.actions import UiActionAdvancePresentation, UiActionChooseCard, UiActionChooseRow
from row_taker.client.game_client_core import GameClientCore
from row_taker.engine.game.phases import Phase
from row_taker.engine.game.player_state_ops import playable_cards, selectable_row_ids
from row_taker.protocol.messages import ClientToServerMessage, ServerToClientMessage


@dataclass(slots=True)
class RandomBotClient:
    rng: random.Random = field(default_factory=random.Random)
    core: GameClientCore = field(default_factory=lambda: GameClientCore(state=initial_cli_state()))

    def handle_server_message(self, message: ServerToClientMessage) -> tuple[ClientToServerMessage, ...]:
        update = self.core.on_server_message(message)
        outbound_messages: list[ClientToServerMessage] = list(update.outbound_messages)
        self._drain_presentation(outbound_messages)
        self._maybe_act(outbound_messages)
        return tuple(outbound_messages)

    def _drain_presentation(self, outbound_messages: list[ClientToServerMessage]) -> None:
        while has_pending_presentation(self.core.state):
            update = self.core.on_ui_action(UiActionAdvancePresentation())
            outbound_messages.extend(update.outbound_messages)

    def _maybe_act(self, outbound_messages: list[ClientToServerMessage]) -> None:
        state = self.core.state
        player_state = state.player_state
        if player_state is None:
            return

        if state.pending_action.value == 'choose_card':
            player_state.validate_phase(Phase.CHOOSE_CARD)
            player_state.validate_hand_not_empty()
            card = self.rng.choice(playable_cards(player_state))
            update = self.core.on_ui_action(UiActionChooseCard(card_value=card.value))
            outbound_messages.extend(update.outbound_messages)
            return

        if state.pending_action.value == 'choose_row':
            player_state.validate_phase(Phase.CHOOSE_ROW)
            row_id = self.rng.choice(list(selectable_row_ids(player_state)))
            update = self.core.on_ui_action(UiActionChooseRow(row_id=row_id))
            outbound_messages.extend(update.outbound_messages)
