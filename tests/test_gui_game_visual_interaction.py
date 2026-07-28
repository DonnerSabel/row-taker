from __future__ import annotations

from dataclasses import replace

import pytest

pygame = pytest.importorskip("pygame")

from row_taker.client.actions import ClientActionChooseRow
from row_taker.engine.game.cards import Card
from row_taker.engine.game.models import Row, RowID
from row_taker.engine.game.state import PlayerState
from row_taker.gui.layout import compute_layout
from row_taker.gui.screens.game_frame import GameFrame
from row_taker.gui_workbench.scenarios import get_scenario


def _unsorted_choose_row_state():
    state = get_scenario("choose-row").state
    assert state.public_state is not None
    assert state.player_state is not None
    rows = (
        Row(RowID("high"), (Card(90),)),
        Row(RowID("low"), (Card(13),)),
        Row(RowID("middle"), (Card(45),)),
        Row(RowID("upper"), (Card(72),)),
    )
    phase_info = replace(
        state.public_state.phase_info,
        selectable_row_ids=tuple(row.row_id for row in rows),
    )
    public_state = replace(state.public_state, rows=rows, phase_info=phase_info)
    player_state = PlayerState(
        public_state=public_state,
        self_player_id=state.player_state.self_player_id,
        hand=state.player_state.hand,
    )
    return replace(
        state,
        core_state=replace(
            state.core_state,
            public_state=public_state,
            player_state=player_state,
        ),
    )


def test_row_targets_follow_visual_order_but_return_stable_row_ids() -> None:
    frame = GameFrame.from_layout(
        layout=compute_layout(1600, 900),
        state=_unsorted_choose_row_state(),
        presentation_elapsed_frames=0,
        mouse_pos=(-1, -1),
    )

    assert [row.row_id for row in frame.visual_state.rows] == [
        RowID("low"),
        RowID("middle"),
        RowID("upper"),
        RowID("high"),
    ]
    assert [target.row_id for target in frame.targets.row_targets] == [
        RowID("low"),
        RowID("middle"),
        RowID("upper"),
        RowID("high"),
    ]

    first_target = frame.targets.row_targets[0]
    result = frame.handle_event(
        pygame.event.Event(
            pygame.MOUSEBUTTONDOWN,
            button=1,
            pos=first_target.rect.center,
        )
    )

    assert result.client_action == ClientActionChooseRow(row_id=RowID("low"))
