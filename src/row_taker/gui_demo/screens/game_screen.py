from __future__ import annotations

from dataclasses import dataclass

import pygame

from row_taker.client.actions import (
    ClientActionAdvancePresentation,
    ClientActionChooseCard,
    ClientActionChooseRow,
)
from row_taker.client.presentation_events import (
    PresentationCardsRevealed,
    PresentationEvent,
    PresentationOverflowResolved,
    PresentationRowChoiceRequired,
    PresentationRowChosen,
    PresentationRowTaken,
    PresentationTrickFinished,
)
from row_taker.client.state import ClientState
from row_taker.engine.game import Phase
from row_taker.gui_demo.layout import DemoLayout
from row_taker.gui_demo.primitives import ACCENT, TEXT_MUTED, WINDOW_BACKGROUND, PrimitiveDrawer
from row_taker.gui_demo.ui.screen_result import NO_SCREEN_RESULT, ScreenResult


@dataclass(frozen=True, slots=True)
class CardTarget:
    card_value: int
    rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class RowTarget:
    row_id: object
    rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class ContinueTarget:
    rect: pygame.Rect


@dataclass(frozen=True, slots=True)
class GameScreenTargets:
    card_targets: tuple[CardTarget, ...] = ()
    row_targets: tuple[RowTarget, ...] = ()
    continue_target: ContinueTarget | None = None


def build_game_screen_targets(layout: DemoLayout, state: ClientState) -> GameScreenTargets:
    return GameScreenTargets(
        card_targets=_build_card_targets(layout, state),
        row_targets=_build_row_targets(layout, state),
        continue_target=_build_continue_target(layout, state),
    )


def handle_game_event(
    event: pygame.event.Event,
    *,
    state: ClientState | None,
    game_targets: GameScreenTargets | None,
) -> ScreenResult:
    if event.type == pygame.QUIT:
        return ScreenResult(request_quit=True)
    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
        return ScreenResult(request_quit=True)
    if state is None or game_targets is None:
        return NO_SCREEN_RESULT
    if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE and state.pending_presentation_events:
        return ScreenResult(client_action=ClientActionAdvancePresentation())
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        return _handle_left_click(event.pos, game_targets=game_targets)
    return NO_SCREEN_RESULT


def render_game_screen(
    screen: pygame.Surface,
    *,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
    frame_count: int,
    game_targets: GameScreenTargets,
    last_action_summary: str,
) -> None:
    screen.fill(WINDOW_BACKGROUND)
    _render_header(screen, drawer, layout, client_state)
    _render_game_panels(screen, drawer, layout, client_state, game_targets)
    _render_sidebar(screen, drawer, layout, client_state, frame_count, last_action_summary, game_targets)
    _render_footer(screen, drawer, layout)


def _handle_left_click(position: tuple[int, int], *, game_targets: GameScreenTargets) -> ScreenResult:
    for target in game_targets.card_targets:
        if target.rect.collidepoint(position):
            return ScreenResult(client_action=ClientActionChooseCard(card_value=target.card_value))

    for target in game_targets.row_targets:
        if target.rect.collidepoint(position):
            return ScreenResult(client_action=ClientActionChooseRow(row_id=target.row_id))

    if game_targets.continue_target is not None and game_targets.continue_target.rect.collidepoint(position):
        return ScreenResult(client_action=ClientActionAdvancePresentation())

    return NO_SCREEN_RESULT


def _build_card_targets(layout: DemoLayout, state: ClientState) -> tuple[CardTarget, ...]:
    player_state = state.player_state
    if player_state is None:
        return ()

    hand_rect = layout.main_bottom_rect.inflate(-24, -24)

    info_lines = [
        f'player: {player_state.self_player_name()}',
        f'pending_action: {state.pending_action.value}',
        'click a card to send the choice',
    ]
    if player_state.phase_info.phase.value == 'choose_row' and player_state.pending_card_value() is not None:
        info_lines.append(f'pending_card: {player_state.pending_card_value()}')

    info_line_height = 22
    info_gap = 6
    info_height = len(info_lines) * info_line_height + max(0, len(info_lines) - 1) * info_gap
    cards_top = hand_rect.top + info_height + 10

    card_width = 78
    card_height = 58
    row_gap = 10
    col_gap = 10
    columns = max(1, hand_rect.width // (card_width + col_gap))

    targets: list[CardTarget] = []
    for index, card in enumerate(player_state.hand):
        row_index = index // columns
        column_index = index % columns
        rect = pygame.Rect(
            hand_rect.left + column_index * (card_width + col_gap),
            cards_top + row_index * (card_height + row_gap),
            card_width,
            card_height,
        )
        targets.append(CardTarget(card_value=card.value, rect=rect))
    return tuple(targets)


def _build_row_targets(layout: DemoLayout, state: ClientState) -> tuple[RowTarget, ...]:
    player_state = state.player_state
    public_state = state.public_state
    if player_state is None or public_state is None:
        return ()
    if player_state.phase_info.phase.value != 'choose_row':
        return ()

    top_rect = layout.main_top_rect.inflate(-24, -24)

    info_lines = [
        f'round={public_state.round_no} trick={public_state.trick_no} phase={public_state.phase_info.phase.value}',
        f'message: {public_state.phase_info.message or "-"}',
    ]
    info_line_height = 22
    info_gap = 6
    info_height = len(info_lines) * info_line_height + max(0, len(info_lines) - 1) * info_gap
    rows_top = top_rect.top + info_height + 10

    row_area_height = 132
    row_width = max(120, (top_rect.width - 18) // max(1, len(public_state.rows)))

    selectable = set(player_state.get_selectable_row_ids_for_choose_row())
    targets: list[RowTarget] = []
    for index, row in enumerate(public_state.rows):
        if row.row_id not in selectable:
            continue
        rect = pygame.Rect(
            top_rect.left + index * row_width,
            rows_top,
            row_width - 8,
            row_area_height,
        )
        targets.append(RowTarget(row_id=row.row_id, rect=rect))
    return tuple(targets)


def _build_continue_target(layout: DemoLayout, state: ClientState) -> ContinueTarget | None:
    if not state.pending_presentation_events:
        return None
    rect = pygame.Rect(
        layout.sidebar_rect.left + 20,
        layout.sidebar_rect.bottom - 54,
        layout.sidebar_rect.width - 40,
        34,
    )
    return ContinueTarget(rect=rect)


def _render_header(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
) -> None:
    content_rect = drawer.draw_panel(screen, layout.header_rect)
    drawer.draw_text(screen, 'Row-Taker GUI Demo', (content_rect.left, content_rect.top), role='title')
    subtitle = (
        'Einfaches pygame-Frontend auf dem gemeinsamen ClientState. '
        f'Mode={client_state.client_mode.value}, pending_action={client_state.pending_action.value}'
    )
    drawer.draw_text(
        screen,
        subtitle,
        (content_rect.left, content_rect.top + 34),
        role='small',
        color=TEXT_MUTED,
    )


def _render_game_panels(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
    game_targets: GameScreenTargets,
) -> None:
    top_content = drawer.draw_panel(screen, layout.main_top_rect, title='Rows and players')
    bottom_content = drawer.draw_panel(screen, layout.main_bottom_rect, title='Own hand')

    _render_rows_and_players(screen, drawer, top_content, client_state, game_targets)
    _render_hand(screen, drawer, bottom_content, client_state, game_targets)


def _render_rows_and_players(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    client_state: ClientState,
    game_targets: GameScreenTargets,
) -> None:
    public_state = client_state.public_state
    if public_state is None:
        drawer.draw_wrapped_lines(screen, ['No public_state available.'], rect)
        return

    info_lines = [
        f'round={public_state.round_no} trick={public_state.trick_no} phase={public_state.phase_info.phase.value}',
        f'message: {public_state.phase_info.message or "-"}',
    ]
    info_height = drawer.measure_wrapped_lines(info_lines, max_width=rect.width, role='small')
    info_rect = rect.copy()
    info_rect.height = info_height
    info_bottom = drawer.draw_wrapped_lines(screen, info_lines, info_rect, role='small', color=TEXT_MUTED)

    y = info_bottom + 10
    row_target_by_id = {target.row_id: target for target in game_targets.row_targets}
    row_area_height = 132
    row_width = max(120, (rect.width - 18) // max(1, len(public_state.rows)))

    for index, row in enumerate(public_state.rows):
        target_rect = row_target_by_id[row.row_id].rect if row.row_id in row_target_by_id else None
        fallback_rect = rect.copy()
        fallback_rect.left = rect.left + index * row_width
        fallback_rect.top = y
        fallback_rect.width = row_width - 8
        fallback_rect.height = row_area_height
        _draw_row(
            screen,
            drawer,
            target_rect or fallback_rect,
            row.row_id,
            row.cards,
            selectable=_is_row_selectable(client_state, row.row_id),
        )

    players_top = y + row_area_height + 20
    drawer.draw_text(screen, 'Scores', (rect.left, players_top), role='small', color=TEXT_MUTED)
    players_y = players_top + 22
    for player in public_state.players:
        marker = ' <you>' if player.player_id == client_state.own_player_id else ''
        line = f'{player.name}: {player.score} points, {player.hand_count} cards{marker}'
        drawer.draw_text(screen, line, (rect.left, players_y), role='body')
        players_y += 26


def _render_hand(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    client_state: ClientState,
    game_targets: GameScreenTargets,
) -> None:
    player_state = client_state.player_state
    if player_state is None:
        drawer.draw_wrapped_lines(screen, ['No player_state available.'], rect)
        return

    info_lines = [
        f'player: {player_state.self_player_name()}',
        f'pending_action: {client_state.pending_action.value}',
        'click a card to send the choice',
    ]
    if player_state.phase_info.phase == Phase.CHOOSE_ROW and player_state.pending_card_value() is not None:
        info_lines.append(f'pending_card: {player_state.pending_card_value()}')

    info_height = drawer.measure_wrapped_lines(info_lines, max_width=rect.width, role='small')
    info_rect = rect.copy()
    info_rect.height = info_height
    drawer.draw_wrapped_lines(screen, info_lines, info_rect, role='small', color=TEXT_MUTED)

    target_by_value = {target.card_value: target for target in game_targets.card_targets}
    for card in player_state.hand:
        target = target_by_value.get(card.value)
        if target is None:
            continue
        drawer.draw_card(screen, target.rect, value=card.value, bullheads=card.bullheads)

    if player_state.phase_info.phase == Phase.CHOOSE_ROW and player_state.pending_card_value() is not None:
        hint_rect = rect.copy()
        hint_rect.left = rect.right - 140
        hint_rect.top = rect.top
        hint_rect.width = 120
        hint_rect.height = 32
        drawer.draw_badge(screen, hint_rect, text=f'take {player_state.pending_card_value()}', active=True)


def _draw_row(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    rect: pygame.Rect,
    row_id: object,
    cards: list[object],
    *,
    selectable: bool,
) -> None:
    content_rect = drawer.draw_panel(screen, rect, title=str(row_id))
    drawer.draw_text(
        screen,
        f'bullheads={sum(card.bullheads for card in cards)}',
        (content_rect.left, content_rect.top),
        role='small',
        color=ACCENT if selectable else TEXT_MUTED,
    )
    card_y = content_rect.top + 24
    for index, card in enumerate(cards):
        card_rect = content_rect.copy()
        card_rect.left = content_rect.left + index * 72
        card_rect.top = card_y
        card_rect.width = 64
        card_rect.height = 52
        drawer.draw_card(screen, card_rect, value=card.value, bullheads=card.bullheads, selected=selectable)


def _is_row_selectable(client_state: ClientState, row_id: object) -> bool:
    player_state = client_state.player_state
    if player_state is None:
        return False
    if player_state.phase_info.phase != Phase.CHOOSE_ROW:
        return False
    return row_id in player_state.get_selectable_row_ids_for_choose_row()


def _render_sidebar(
    screen: pygame.Surface,
    drawer: PrimitiveDrawer,
    layout: DemoLayout,
    client_state: ClientState,
    frame_count: int,
    last_action_summary: str,
    game_targets: GameScreenTargets,
) -> None:
    content_rect = drawer.draw_panel(screen, layout.sidebar_rect, title='State summary')
    y = content_rect.top

    entries = [
        ('client_mode', client_state.client_mode.value),
        ('pending_action', client_state.pending_action.value),
        ('own_client_id', client_state.own_client_id or '-'),
        ('own_player_id', client_state.own_player_id or '-'),
        ('lobby_submenu', client_state.navigation_state.lobby_submenu),
        ('session_error', client_state.session_error or '-'),
        ('presentation', str(len(client_state.pending_presentation_events))),
        ('frame', str(frame_count)),
    ]

    for key, value in entries:
        drawer.draw_key_value(screen, key, value, (content_rect.left, y))
        y += 28

    drawer.draw_text(screen, 'last_gui_action', (content_rect.left, y + 6), role='small', color=TEXT_MUTED)
    action_rect = content_rect.copy()
    action_rect.top = y + 28
    action_rect.height = 72
    drawer.draw_wrapped_lines(screen, [last_action_summary], action_rect, role='small', color=ACCENT)

    flash_text = client_state.flash_message.text if client_state.flash_message is not None else 'No flash message'
    drawer.draw_text(screen, 'flash_message', (content_rect.left, action_rect.bottom + 10), role='small', color=TEXT_MUTED)
    flash_rect = content_rect.copy()
    flash_rect.top = action_rect.bottom + 32
    flash_rect.height = 64
    drawer.draw_wrapped_lines(screen, [flash_text], flash_rect, role='body', color=ACCENT)

    events_rect = content_rect.copy()
    events_rect.top = flash_rect.bottom + 18
    events_bottom = layout.sidebar_rect.bottom - 70
    events_rect.height = max(40, events_bottom - events_rect.top)
    drawer.draw_text(screen, 'presentation events', (events_rect.left, events_rect.top), role='small', color=TEXT_MUTED)
    events_rect.top += 22
    event_lines = [_format_presentation_event(event) for event in client_state.pending_presentation_events]
    if not event_lines:
        event_lines = ['No pending presentation events.']
    drawer.draw_wrapped_lines(screen, event_lines, events_rect, role='small')

    if game_targets.continue_target is not None:
        drawer.draw_badge(screen, game_targets.continue_target.rect, text='Continue [Space]', active=True)


def _format_presentation_event(event: PresentationEvent) -> str:
    if isinstance(event, PresentationCardsRevealed):
        cards = ', '.join(f'{play.player_name}:{play.card_value}' for play in event.plays)
        return f'cards revealed -> {cards}'
    if isinstance(event, PresentationRowChoiceRequired):
        return f'row choice required -> {event.player_name} with {event.card_value}'
    if isinstance(event, PresentationRowChosen):
        return f'row chosen -> {event.player_name} takes {event.row_id}'
    if isinstance(event, PresentationRowTaken):
        return f'row taken -> {event.player_name} got {event.bullheads} bullheads'
    if isinstance(event, PresentationOverflowResolved):
        return f'overflow resolved -> {event.player_name} got {event.bullheads} bullheads'
    if isinstance(event, PresentationTrickFinished):
        return 'trick finished'
    return event.__class__.__name__


def _render_footer(screen: pygame.Surface, drawer: PrimitiveDrawer, layout: DemoLayout) -> None:
    content_rect = drawer.draw_panel(screen, layout.footer_rect)
    drawer.draw_wrapped_lines(
        screen,
        [
            'ESC quit',
            'Space continue presentation',
            'Mouse for cards, rows and continue',
        ],
        content_rect,
        role='small',
        color=TEXT_MUTED,
    )
