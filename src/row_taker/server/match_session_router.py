from __future__ import annotations

import logging
from dataclasses import dataclass, field, replace

from row_taker.engine.game.models import PlayerID
from row_taker.engine.game.phases import Phase
from row_taker.engine.game.player_state_ops import (
    validate_submit_card,
    validate_submit_row_choice,
)
from row_taker.engine.game.state import GameState, PublicState
from row_taker.hub.match_hub import MatchHub
from row_taker.protocol.messages import (
    CardsRevealed,
    ChooseCardRequested,
    ChooseRowRequested,
    GameServerMessage,
    RevisionedGameServerMessage,
    RowChoiceCommitted,
    SessionEnded,
    SessionEndReason,
    StateUpdated,
    SubmitCard,
    SubmitRowChoice,
    is_revisioned_game_message,
)
from row_taker.server.errors import ClientRequestRejected
from row_taker.server.match_participants import MatchParticipants
from row_taker.server.outgoing import OutgoingEnvelope

logger = logging.getLogger("row_taker.server.match_session")


@dataclass(slots=True)
class MatchSessionRouter:
    active_match: MatchHub | None = None
    player_to_client_id: dict[PlayerID, str] = field(default_factory=dict)
    client_to_player_id: dict[str, PlayerID] = field(default_factory=dict)
    _next_game_revision: int = 1
    _outbox: list[OutgoingEnvelope] = field(default_factory=list)

    @property
    def is_active(self) -> bool:
        return self.active_match is not None

    @property
    def state(self) -> GameState:
        if self.active_match is None:
            raise ValueError("no active match")
        return self.active_match.state

    def build_public_state(self) -> PublicState:
        if self.active_match is None:
            raise ValueError("no active match")
        return self.active_match.build_public_state()

    def start(self, state: GameState, participants: MatchParticipants) -> None:
        if self.active_match is not None:
            raise RuntimeError("match session already active")
        self.active_match = MatchHub(state=state)
        self.player_to_client_id = dict(participants.player_to_client_id)
        self.client_to_player_id = dict(participants.client_to_player_id)
        self._next_game_revision = 1
        self.active_match.start_match()
        self._drive_until_idle()

    def handle_client_message(
        self,
        client_id: str,
        message: SubmitCard | SubmitRowChoice,
    ) -> None:
        if self.active_match is None:
            raise ClientRequestRejected("game message received before game start")
        player_id = self.client_to_player_id.get(client_id)
        if player_id is None:
            raise ClientRequestRejected("client is not assigned to a player")
        self._validate_game_message(player_id, message)
        self.active_match.handle_client_message(player_id, message)
        self._drive_until_idle()

    def abort(
        self,
        *,
        departing_client_id: str,
        departing_display_name: str,
        reason: SessionEndReason,
        message: str,
        remaining_client_ids: tuple[str, ...],
    ) -> None:
        for client_id in remaining_client_ids:
            logger.debug(
                "enqueue SessionEnded: target_client_id=%s reason=%s",
                client_id,
                reason.value,
            )
            self._outbox.append(
                OutgoingEnvelope(
                    SessionEnded(
                        message=message,
                        reason=reason,
                        client_id=departing_client_id,
                        display_name=departing_display_name,
                    ),
                    target_client_id=client_id,
                )
            )
        self.clear()

    def clear(self) -> None:
        self.active_match = None
        self.player_to_client_id.clear()
        self.client_to_player_id.clear()

    def drain_outgoing(self) -> list[OutgoingEnvelope]:
        drained = list(self._outbox)
        self._outbox.clear()
        return drained

    def _validate_game_message(
        self,
        player_id: PlayerID,
        message: SubmitCard | SubmitRowChoice,
    ) -> None:
        if self.active_match is None:
            raise RuntimeError("cannot validate a game message without an active match")

        player_state = self.active_match.build_player_state_for(player_id)
        try:
            if isinstance(message, SubmitCard):
                player_state.validate_phase(Phase.CHOOSE_CARD)
                if player_id in self.active_match.state.selected_cards:
                    raise ValueError(f"player {player_id!r} has already selected a card")
                validate_submit_card(player_state, message.card_value)
                return

            player_state.validate_phase(Phase.CHOOSE_ROW)
            if player_state.phase_info.active_player_id != player_id:
                raise ValueError("row choice requested for a different active player")
            validate_submit_row_choice(player_state, message.row_id)
        except ValueError as exc:
            raise ClientRequestRejected(str(exc)) from exc

    def _drive_until_idle(self) -> None:
        if self.active_match is None:
            return
        while True:
            messages = self.active_match.drain_outbox()
            if not messages:
                return
            for message in messages:
                self._route_match_message(message)

    def _route_match_message(self, message: GameServerMessage) -> None:
        routed_message: GameServerMessage
        if is_revisioned_game_message(message):
            routed_message = self._stamp_game_message_revision(message)
        else:
            routed_message = message
        if isinstance(routed_message, ChooseCardRequested | ChooseRowRequested):
            target_client_id = self.player_to_client_id[routed_message.player_id]
            logger.debug(
                "route match message: type=%s revision=%s target_client_id=%s",
                type(routed_message).__name__,
                routed_message.revision,
                target_client_id,
            )
            self._outbox.append(
                OutgoingEnvelope(
                    message=routed_message,
                    target_client_id=target_client_id,
                )
            )
            return
        revision = routed_message.revision if is_revisioned_game_message(routed_message) else None
        logger.debug(
            "route broadcast match message: type=%s revision=%s",
            type(routed_message).__name__,
            revision,
        )
        self._outbox.append(OutgoingEnvelope(message=routed_message))

    def _stamp_game_message_revision(
        self, message: RevisionedGameServerMessage
    ) -> RevisionedGameServerMessage:
        revision = self._next_game_revision
        self._next_game_revision += 1
        if isinstance(message, StateUpdated):
            return replace(message, revision=revision)
        if isinstance(message, CardsRevealed):
            return replace(message, revision=revision)
        if isinstance(message, RowChoiceCommitted):
            return replace(message, revision=revision)
        if isinstance(message, ChooseCardRequested):
            return replace(message, revision=revision)
        if isinstance(message, ChooseRowRequested):
            return replace(message, revision=revision)
        return replace(message, revision=revision)
