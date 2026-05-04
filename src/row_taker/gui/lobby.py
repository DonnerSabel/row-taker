"""Grafische Lobby-Oberfläche für RowTaker (pygame, plattformübergreifend)."""

from __future__ import annotations

import os
import queue
import threading
from contextlib import suppress
from dataclasses import dataclass, field, replace
from pathlib import Path

import pygame

from row_taker.cli.state_machine import UserInputResult, reduce_server_message, reduce_user_input
from row_taker.cli.state_models import CliState, GameScreen, LobbyScreen, initial_cli_state
from row_taker.protocol.errors import ConnectionClosed
from row_taker.protocol.messages import JoinLobby, ServerToClientMessage
from row_taker.protocol.transport import ClientTransport

# ---------------------------------------------------------------------------
# Farben
# ---------------------------------------------------------------------------
C_BG = (20, 22, 30)
C_PANEL = (15, 18, 28, 220)
C_ACCENT = (0, 180, 220)
C_ACCENT_DIM = (0, 100, 130)
C_GOLD = (220, 180, 50)
C_GREEN = (40, 200, 80)
C_RED = (220, 60, 60)
C_WHITE = (230, 235, 245)
C_GRAY = (140, 145, 160)
C_DARK = (40, 44, 55)
C_SEAT_EMPTY = (50, 55, 70, 180)
C_SEAT_SELF = (0, 120, 160, 200)
C_SEAT_BOT = (80, 60, 30, 200)
C_SEAT_OTHER = (50, 70, 50, 200)
C_BTN = (0, 140, 180)
C_BTN_HOVER = (0, 180, 220)
C_BTN_DANGER = (180, 40, 40)
C_BTN_DANGER_HOVER = (220, 60, 60)
C_BTN_START = (30, 160, 70)
C_BTN_START_HOVER = (40, 200, 90)
C_INPUT_BG = (30, 34, 48, 240)
C_INPUT_BORDER = (0, 180, 220)
C_FLASH_ERROR = (180, 40, 40)
C_FLASH_INFO = (0, 140, 180)

WIN_W, WIN_H = 1024, 700
FPS = 60
SEAT_W, SEAT_H = 140, 100
SEAT_GAP = 18
BTN_W, BTN_H = 180, 42


# ---------------------------------------------------------------------------
# Zeichen-Helfer
# ---------------------------------------------------------------------------

def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _alpha_surf(w: int, h: int, color: tuple) -> pygame.Surface:
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill(color)
    return s


def _rounded_rect(surf: pygame.Surface, rect: pygame.Rect, color: tuple, radius: int = 8) -> None:
    tmp = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(tmp, color, tmp.get_rect(), border_radius=radius)
    surf.blit(tmp, rect.topleft)


def _draw_text(
    surf: pygame.Surface, font: pygame.font.Font, text: str,
    pos: tuple[int, int], color: tuple = C_WHITE, center: bool = False,
    max_width: int | None = None,
) -> pygame.Rect:
    rendered = font.render(text, True, color)
    if max_width and rendered.get_width() > max_width:
        while len(text) > 1 and font.render(text + "…", True, color).get_width() > max_width:
            text = text[:-1]
        rendered = font.render(text + "…", True, color)
    r = rendered.get_rect()
    if center:
        r.center = pos
    else:
        r.topleft = pos
    surf.blit(rendered, r)
    return r


# ---------------------------------------------------------------------------
# Button
# ---------------------------------------------------------------------------

@dataclass
class Button:
    rect: pygame.Rect
    label: str
    action: str
    color: tuple = C_BTN
    hover_color: tuple = C_BTN_HOVER
    visible: bool = True
    _hovered: bool = False

    def draw(self, surf: pygame.Surface, font: pygame.font.Font) -> None:
        if not self.visible:
            return
        col = self.hover_color if self._hovered else self.color
        _rounded_rect(surf, self.rect, col, radius=6)
        _draw_text(surf, font, self.label, self.rect.center, C_WHITE, center=True)

    def update_hover(self, pos: tuple[int, int]) -> None:
        self._hovered = self.visible and self.rect.collidepoint(pos)

    def clicked(self, pos: tuple[int, int]) -> bool:
        return self.visible and self.rect.collidepoint(pos)


# ---------------------------------------------------------------------------
# TextInput (Modal-Overlay)
# ---------------------------------------------------------------------------

@dataclass
class TextInput:
    prompt_text: str = ""
    text: str = ""
    active: bool = False
    max_len: int = 24

    def draw(self, surf: pygame.Surface, font: pygame.font.Font, font_sm: pygame.font.Font) -> None:
        if not self.active:
            return
        surf.blit(_alpha_surf(WIN_W, WIN_H, (0, 0, 0, 160)), (0, 0))
        bw, bh = 420, 170
        bx, by = (WIN_W - bw) // 2, (WIN_H - bh) // 2
        box = pygame.Rect(bx, by, bw, bh)
        _rounded_rect(surf, box, C_PANEL, radius=12)
        pygame.draw.rect(surf, C_ACCENT, box, 2, border_radius=12)
        _draw_text(surf, font, self.prompt_text, (box.centerx, by + 30), C_ACCENT, center=True)
        inp = pygame.Rect(bx + 30, by + 65, bw - 60, 40)
        _rounded_rect(surf, inp, C_INPUT_BG, radius=4)
        pygame.draw.rect(surf, C_INPUT_BORDER, inp, 2, border_radius=4)
        cursor = self.text + ("|" if pygame.time.get_ticks() % 1000 < 500 else "")
        _draw_text(surf, font, cursor, (inp.x + 8, inp.centery - 9), C_WHITE)
        _draw_text(surf, font_sm, "Enter = Bestätigen   Esc = Abbrechen",
                   (box.centerx, by + bh - 28), C_GRAY, center=True)

    def handle_key(self, event: pygame.event.Event) -> str | None:
        if not self.active:
            return None
        if event.key == pygame.K_RETURN:
            return "submit"
        if event.key == pygame.K_ESCAPE:
            return "cancel"
        if event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]
        elif event.unicode and len(self.text) < self.max_len and event.unicode.isprintable():
            self.text += event.unicode
        return None


# ---------------------------------------------------------------------------
# SeatWidget
# ---------------------------------------------------------------------------

@dataclass
class SeatWidget:
    index: int
    rect: pygame.Rect
    occupant_name: str | None = None
    occupant_kind: str | None = None
    is_self: bool = False
    _hovered: bool = False

    def draw(self, surf: pygame.Surface, font: pygame.font.Font, font_sm: pygame.font.Font) -> None:
        if self.occupant_name is None:
            base = C_SEAT_EMPTY
        elif self.is_self:
            base = C_SEAT_SELF
        elif self.occupant_kind == "bot":
            base = C_SEAT_BOT
        else:
            base = C_SEAT_OTHER
        col = tuple(_clamp(c + (25 if self._hovered else 0), 0, 255) for c in base)
        _rounded_rect(surf, self.rect, col, radius=10)
        border = C_ACCENT if self._hovered else (*C_ACCENT_DIM[:3], 80)
        pygame.draw.rect(surf, border, self.rect, 2, border_radius=10)
        cx = self.rect.centerx
        _draw_text(surf, font_sm, f"Platz {self.index}", (cx, self.rect.y + 14), C_GRAY, center=True)
        if self.occupant_name:
            _draw_text(surf, font, self.occupant_name, (cx, self.rect.centery + 2),
                       C_WHITE, center=True, max_width=SEAT_W - 16)
            tag = "Du" if self.is_self else (self.occupant_kind or "")
            _draw_text(surf, font_sm, tag, (cx, self.rect.bottom - 22),
                       C_GOLD if self.is_self else C_GRAY, center=True)
        else:
            _draw_text(surf, font, "(leer)", (cx, self.rect.centery + 2), C_GRAY, center=True)

    def update_hover(self, pos: tuple[int, int]) -> None:
        self._hovered = self.rect.collidepoint(pos)

    def clicked(self, pos: tuple[int, int]) -> bool:
        return self.rect.collidepoint(pos)


# ---------------------------------------------------------------------------
# SeatContextMenu
# ---------------------------------------------------------------------------

@dataclass
class SeatContextMenu:
    seat_index: int = -1
    buttons: list[Button] = field(default_factory=list)
    visible: bool = False
    rect: pygame.Rect = field(default_factory=lambda: pygame.Rect(0, 0, 0, 0))

    def show_for(self, seat_index: int, anchor: pygame.Rect) -> None:
        self.seat_index = seat_index
        self.visible = True
        bw, bh, gap = 160, 36, 4
        items = [
            ("Mich setzen", "seat_self", C_BTN, C_BTN_HOVER),
            ("Bot setzen", "seat_bot", C_BTN, C_BTN_HOVER),
            ("Platz leeren", "seat_clear", C_BTN_DANGER, C_BTN_DANGER_HOVER),
            ("Zurück", "seat_back", C_DARK, C_GRAY),
        ]
        x = anchor.centerx - bw // 2
        y = anchor.bottom + 6
        total_h = len(items) * (bh + gap)
        if y + total_h > WIN_H - 10:
            y = anchor.top - total_h - 10
        self.buttons = []
        for label, action, col, hcol in items:
            self.buttons.append(Button(pygame.Rect(x, y, bw, bh), label, action, col, hcol))
            y += bh + gap
        self.rect = pygame.Rect(x - 6, self.buttons[0].rect.y - 6, bw + 12,
                                y - self.buttons[0].rect.y + 6)

    def draw(self, surf: pygame.Surface, font: pygame.font.Font) -> None:
        if not self.visible:
            return
        _rounded_rect(surf, self.rect, (20, 24, 35, 235), radius=8)
        for btn in self.buttons:
            btn.draw(surf, font)

    def update_hover(self, pos: tuple[int, int]) -> None:
        for btn in self.buttons:
            btn.update_hover(pos)

    def handle_click(self, pos: tuple[int, int]) -> str | None:
        if not self.visible:
            return None
        for btn in self.buttons:
            if btn.clicked(pos):
                return btn.action
        return None


# ---------------------------------------------------------------------------
# Netzwerk-Thread
# ---------------------------------------------------------------------------

class _ReceiverThread(threading.Thread):
    def __init__(self, transport: ClientTransport, q: queue.Queue) -> None:
        super().__init__(daemon=True)
        self.transport = transport
        self.q = q
        self._stop = threading.Event()

    def run(self) -> None:
        while not self._stop.is_set():
            try:
                msg = self.transport.receive()
                self.q.put(("msg", msg))
            except ConnectionClosed:
                self.q.put(("closed", None))
                break
            except Exception as exc:
                self.q.put(("error", str(exc)))
                break

    def request_stop(self) -> None:
        self._stop.set()


# ---------------------------------------------------------------------------
# LobbyWindow
# ---------------------------------------------------------------------------

class LobbyWindow:

    def __init__(self) -> None:
        self.state: CliState = initial_cli_state()
        self.transport: ClientTransport | None = None
        self.running = False
        self.clock: pygame.time.Clock | None = None
        self._receiver: _ReceiverThread | None = None
        self._msg_queue: queue.Queue = queue.Queue()

        self.screen: pygame.Surface | None = None
        self.bg_image: pygame.Surface | None = None
        self.font: pygame.font.Font | None = None
        self.font_small: pygame.font.Font | None = None
        self.font_title: pygame.font.Font | None = None

        self.seat_widgets: list[SeatWidget] = []
        self.context_menu = SeatContextMenu()
        self.text_input = TextInput()
        self._input_purpose: str = ""
        self._input_seat: int = -1
        self.flash_text: str = ""
        self.flash_level: str = "info"
        self.flash_timer: int = 0

        self.btn_rename = Button(pygame.Rect(0, 0, 0, 0), "Name ändern", "rename")
        self.btn_start = Button(pygame.Rect(0, 0, 0, 0), "Spiel starten", "start",
                                C_BTN_START, C_BTN_START_HOVER)
        self.btn_leave = Button(pygame.Rect(0, 0, 0, 0), "Verlassen", "leave",
                                C_BTN_DANGER, C_BTN_DANGER_HOVER)
        self.buttons: list[Button] = [self.btn_rename, self.btn_start, self.btn_leave]

        self.connection_phase = True
        self.conn_inputs: dict[str, str] = {"host": "127.0.0.1", "port": "8765", "name": "Spieler"}
        self.conn_focus: str = "host"
        self.conn_error: str = ""
        self.game_started = False

    # ---- Init ----

    def open(self) -> None:
        pygame.init()
        pygame.display.set_caption("RowTaker – Lobby")
        icon_path = self._project_root() / "images" / "lobby_bg.png"
        if icon_path.exists():
            with suppress(Exception):
                pygame.display.set_icon(pygame.transform.smoothscale(
                    pygame.image.load(str(icon_path)), (64, 64)))
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.clock = pygame.time.Clock()
        fp = self._find_font()
        self.font = pygame.font.Font(fp, 18)
        self.font_small = pygame.font.Font(fp, 14)
        self.font_title = pygame.font.Font(fp, 32)
        self._load_bg()
        self.running = True

    def _project_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    def _find_font(self) -> str | None:
        for p in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]:
            if os.path.isfile(p):
                return p
        return None

    def _load_bg(self) -> None:
        bg = self._project_root() / "images" / "lobby_bg.png"
        if bg.exists():
            raw = pygame.image.load(str(bg)).convert_alpha()
            self.bg_image = pygame.transform.smoothscale(raw, (WIN_W, WIN_H))

    # ---- Layout ----

    def _layout_seats(self) -> None:
        lobby = self.state.lobby_view
        if lobby is None:
            self.seat_widgets = []
            return
        count = lobby.seat_count
        total_w = count * SEAT_W + (count - 1) * SEAT_GAP
        sx = (WIN_W - total_w) // 2
        sy = 310
        self.seat_widgets = []
        for sv in lobby.seats:
            i = sv.seat_index
            x = sx + i * (SEAT_W + SEAT_GAP)
            me = sv.occupant_client_id is not None and sv.occupant_client_id == self.state.own_client_id
            self.seat_widgets.append(SeatWidget(i, pygame.Rect(x, sy, SEAT_W, SEAT_H),
                                                sv.occupant_display_name, sv.occupant_kind, me))
        by = 480
        tw = 3 * BTN_W + 2 * 20
        bx = (WIN_W - tw) // 2
        self.btn_rename.rect = pygame.Rect(bx, by, BTN_W, BTN_H)
        self.btn_start.rect = pygame.Rect(bx + BTN_W + 20, by, BTN_W, BTN_H)
        self.btn_leave.rect = pygame.Rect(bx + 2 * (BTN_W + 20), by, BTN_W, BTN_H)

    # ---- Draw ----

    def _draw(self) -> None:
        if not self.screen or not self.font:
            return
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
        else:
            self.screen.fill(C_BG)

        if self.connection_phase:
            self._draw_connect_dialog()
            pygame.display.flip()
            return

        # Titel
        _rounded_rect(self.screen, pygame.Rect(20, 15, WIN_W - 40, 60), C_PANEL, radius=10)
        _draw_text(self.screen, self.font_title, "ROWTAKER", (WIN_W // 2 - 90, 22), C_ACCENT)
        _draw_text(self.screen, self.font_title, "LOBBY", (WIN_W // 2 + 90, 22), C_GOLD)

        lobby = self.state.lobby_view
        if lobby and lobby.server_endpoint:
            _draw_text(self.screen, self.font_small, f"Server: {lobby.server_endpoint}", (40, 88), C_GRAY)
        own = self._own_display_name()
        if own:
            _draw_text(self.screen, self.font, f"Dein Name: {own}", (WIN_W - 280, 88), C_WHITE)

        # Teilnehmer
        self._draw_participants()

        # Sitzplätze
        sp = pygame.Rect(20, 260, WIN_W - 40, 185)
        _rounded_rect(self.screen, sp, C_PANEL, radius=10)
        _draw_text(self.screen, self.font, "Sitzplätze  (Klick zum Bearbeiten)", (40, 272), C_ACCENT)
        for sw in self.seat_widgets:
            sw.draw(self.screen, self.font, self.font_small)

        for btn in self.buttons:
            btn.draw(self.screen, self.font)

        self._draw_status_bar()
        self.context_menu.draw(self.screen, self.font_small)
        if self.flash_timer > 0:
            self._draw_flash()
        self.text_input.draw(self.screen, self.font, self.font_small)
        pygame.display.flip()

    def _draw_participants(self) -> None:
        lobby = self.state.lobby_view
        if not lobby:
            return
        _rounded_rect(self.screen, pygame.Rect(20, 110, WIN_W - 40, 140), C_PANEL, radius=10)
        _draw_text(self.screen, self.font, "Teilnehmer:", (40, 122), C_ACCENT)
        parts = sorted(lobby.participants,
                       key=lambda p: (p.seat_index is None, p.seat_index or 9999, p.display_name.lower()))
        cw = 240
        for i, p in enumerate(parts):
            px = 40 + (i % 4) * cw
            py = 150 + (i // 4) * 26
            mk = " ★" if p.client_id == self.state.own_client_id else ""
            ss = f"P{p.seat_index}" if p.seat_index is not None else "—"
            _draw_text(self.screen, self.font_small,
                       f"[{ss}] {p.display_name} ({p.participant_kind}){mk}",
                       (px, py), C_GOLD if p.participant_kind == "bot" else C_WHITE, max_width=cw - 10)

    def _draw_status_bar(self) -> None:
        bar = pygame.Rect(20, WIN_H - 55, WIN_W - 40, 40)
        _rounded_rect(self.screen, bar, C_PANEL, radius=8)
        lobby = self.state.lobby_view
        if not lobby:
            _draw_text(self.screen, self.font_small, "Verbunden – warte auf Lobby-Daten…",
                       bar.center, C_GRAY, center=True)
            return
        occ = sum(1 for s in lobby.seats if s.occupant_display_name is not None)
        tot = lobby.seat_count
        if occ < tot:
            txt, col = f"{occ}/{tot} Plätze besetzt – alle müssen belegt sein zum Starten", C_GRAY
        else:
            txt, col = f"Alle {tot} Plätze besetzt – bereit zum Starten!", C_GREEN
        _draw_text(self.screen, self.font_small, txt, bar.center, col, center=True)

    def _draw_flash(self) -> None:
        fc = C_FLASH_ERROR if self.flash_level == "error" else C_FLASH_INFO
        r = pygame.Rect(100, WIN_H - 105, WIN_W - 200, 40)
        _rounded_rect(self.screen, r, (*fc, 210), radius=8)
        _draw_text(self.screen, self.font, self.flash_text, r.center, C_WHITE, center=True, max_width=r.w - 20)

    def _draw_connect_dialog(self) -> None:
        if self.bg_image:
            self.screen.blit(self.bg_image, (0, 0))
        self.screen.blit(_alpha_surf(WIN_W, WIN_H, (0, 0, 0, 180)), (0, 0))
        bw, bh = 450, 370
        bx, by = (WIN_W - bw) // 2, (WIN_H - bh) // 2
        box = pygame.Rect(bx, by, bw, bh)
        _rounded_rect(self.screen, box, C_PANEL, radius=14)
        pygame.draw.rect(self.screen, C_ACCENT, box, 2, border_radius=14)
        _draw_text(self.screen, self.font_title, "VERBINDEN", (box.centerx, by + 35), C_ACCENT, center=True)
        fields = [("host", "Server-IP:"), ("port", "Port:"), ("name", "Dein Name:")]
        y = by + 80
        for key, label in fields:
            focused = self.conn_focus == key
            _draw_text(self.screen, self.font, label, (bx + 40, y), C_GRAY)
            ir = pygame.Rect(bx + 40, y + 26, bw - 80, 38)
            _rounded_rect(self.screen, ir, C_INPUT_BG, radius=4)
            pygame.draw.rect(self.screen, C_ACCENT if focused else C_DARK, ir, 2, border_radius=4)
            t = self.conn_inputs[key]
            if focused:
                t += "|" if pygame.time.get_ticks() % 1000 < 500 else ""
            _draw_text(self.screen, self.font, t, (ir.x + 8, ir.centery - 9), C_WHITE)
            y += 74
        if self.conn_error:
            _draw_text(self.screen, self.font_small, self.conn_error, (box.centerx, y + 8), C_RED, center=True)
        _draw_text(self.screen, self.font_small,
                   "Tab = Feld wechseln  |  Enter = Verbinden  |  Esc = Beenden",
                   (box.centerx, by + bh - 28), C_GRAY, center=True)

    # ---- Helfer ----

    def _own_display_name(self) -> str | None:
        lobby = self.state.lobby_view
        if not lobby or not self.state.own_client_id:
            return None
        for p in lobby.participants:
            if p.client_id == self.state.own_client_id:
                return p.display_name
        return None

    def _show_flash(self, text: str, level: str = "info") -> None:
        self.flash_text = text
        self.flash_level = level
        self.flash_timer = FPS * 4

    def _sync_flash(self) -> None:
        if self.state.flash_message:
            self._show_flash(self.state.flash_message.text, self.state.flash_message.level)

    # ---- State-Machine ----

    def _send_input(self, text: str) -> None:
        result: UserInputResult = reduce_user_input(self.state, text)
        self.state = result.state
        if result.outbound_message is not None and self.transport is not None:
            with suppress(Exception):
                self.transport.send(result.outbound_message)
        self._sync_flash()
        self._layout_seats()

    def _receive_server_message(self, message: ServerToClientMessage) -> None:
        self.state = reduce_server_message(self.state, message)
        self._layout_seats()
        self._sync_flash()
        if isinstance(self.state.screen, GameScreen):
            self.game_started = True

    # ---- Events ----

    def _handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            if not self.connection_phase and self.transport:
                self._send_input("X")
            self.running = False
            return

        if self.connection_phase:
            self._handle_connect_event(event)
            return

        if self.text_input.active:
            if event.type == pygame.KEYDOWN:
                r = self.text_input.handle_key(event)
                if r == "submit":
                    self._on_text_submit()
                elif r == "cancel":
                    self.text_input.active = False
                    self._reset_to_main()
            return

        if event.type == pygame.MOUSEMOTION:
            for sw in self.seat_widgets:
                sw.update_hover(event.pos)
            for btn in self.buttons:
                btn.update_hover(event.pos)
            if self.context_menu.visible:
                self.context_menu.update_hover(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            p = event.pos
            if self.context_menu.visible:
                act = self.context_menu.handle_click(p)
                if act:
                    self._on_context_action(act)
                elif not self.context_menu.rect.collidepoint(p):
                    self.context_menu.visible = False
                return
            for btn in self.buttons:
                if btn.clicked(p):
                    self._on_button(btn.action)
                    return
            for sw in self.seat_widgets:
                if sw.clicked(p):
                    self.context_menu.show_for(sw.index, sw.rect)
                    return

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.context_menu.visible:
                    self.context_menu.visible = False
                else:
                    self._send_input("X")
                    self.running = False
            elif event.key == pygame.K_g:
                self._ensure_main()
                self._send_input("g")
            elif event.key == pygame.K_n:
                self._on_button("rename")

    def _handle_connect_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_TAB:
            order = ["host", "port", "name"]
            self.conn_focus = order[(order.index(self.conn_focus) + 1) % 3]
        elif event.key == pygame.K_RETURN:
            self._try_connect()
        elif event.key == pygame.K_ESCAPE:
            self.running = False
        elif event.key == pygame.K_BACKSPACE:
            k = self.conn_focus
            self.conn_inputs[k] = self.conn_inputs[k][:-1]
        elif event.unicode and event.unicode.isprintable():
            self.conn_inputs[self.conn_focus] += event.unicode

    # ---- Verbindung ----

    def _try_connect(self) -> None:
        host = self.conn_inputs["host"].strip() or "127.0.0.1"
        port_s = self.conn_inputs["port"].strip() or "8765"
        name = self.conn_inputs["name"].strip() or "Spieler"
        try:
            port = int(port_s)
        except ValueError:
            self.conn_error = "Ungültiger Port!"
            return
        if not 1 <= port <= 65535:
            self.conn_error = "Port: 1 – 65535"
            return
        try:
            self.transport = ClientTransport.connect(host, port)
            self.transport.send(JoinLobby(display_name=name))
            self._receiver = _ReceiverThread(self.transport, self._msg_queue)
            self._receiver.start()
            self.connection_phase = False
            self.conn_error = ""
        except Exception as exc:
            self.conn_error = f"Verbindung fehlgeschlagen: {exc}"

    # ---- Aktionen ----

    def _on_button(self, action: str) -> None:
        if action == "rename":
            self.text_input.prompt_text = "Neuen Anzeigenamen eingeben:"
            self.text_input.text = ""
            self.text_input.active = True
            self._input_purpose = "rename"
        elif action == "start":
            self._ensure_main()
            self._send_input("g")
        elif action == "leave":
            self._send_input("X")
            self.running = False

    def _on_context_action(self, action: str) -> None:
        si = self.context_menu.seat_index
        self.context_menu.visible = False
        if action == "seat_self":
            self._ensure_main()
            self._send_input(str(si))
            self._send_input("m")
        elif action == "seat_bot":
            self._ensure_main()
            self._send_input(str(si))
            self.text_input.prompt_text = f"Bot-Name für Platz {si}:"
            self.text_input.text = ""
            self.text_input.active = True
            self._input_purpose = "bot_name"
            self._input_seat = si
        elif action == "seat_clear":
            self._ensure_main()
            self._send_input(str(si))
            self._send_input("c")

    def _on_text_submit(self) -> None:
        text = self.text_input.text.strip()
        self.text_input.active = False
        if self._input_purpose == "rename":
            if text:
                self._ensure_main()
                self._send_input("n")
                self._send_input(text)
            else:
                self._show_flash("Name darf nicht leer sein.", "error")
                self._reset_to_main()
        elif self._input_purpose == "bot_name":
            self._send_input("b")
            self._send_input(text or "")

    def _ensure_main(self) -> None:
        if not isinstance(self.state.screen, LobbyScreen) or self.state.screen.kind != "main":
            self._reset_to_main()

    def _reset_to_main(self) -> None:
        self.state = replace(self.state, screen=LobbyScreen(kind="main"), flash_message=None)

    # ---- Netzwerk-Polling ----

    def _poll_network(self) -> None:
        try:
            while True:
                kind, payload = self._msg_queue.get_nowait()
                if kind == "msg":
                    self._receive_server_message(payload)
                elif kind == "closed":
                    self._show_flash("Verbindung zum Server verloren!", "error")
                elif kind == "error":
                    self._show_flash(f"Netzwerkfehler: {payload}", "error")
        except queue.Empty:
            pass

    # ---- Hauptschleife ----

    def run(self) -> int:
        self.open()
        try:
            while self.running:
                for event in pygame.event.get():
                    self._handle_event(event)
                if not self.connection_phase:
                    self._poll_network()
                if self.flash_timer > 0:
                    self.flash_timer -= 1
                self._draw()
                self.clock.tick(FPS)
                if self.state.should_exit:
                    self.running = False
                if self.game_started:
                    self._show_flash("Spiel startet!", "info")
                    self._draw()
                    pygame.time.wait(1500)
                    self.running = False
            return 0
        finally:
            if self._receiver:
                self._receiver.request_stop()
            if self.transport:
                with suppress(Exception):
                    self.transport.close()
            pygame.quit()
