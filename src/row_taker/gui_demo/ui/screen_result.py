from __future__ import annotations

from dataclasses import dataclass

from row_taker.client.state import ClientState
from row_taker.gui_demo.ui.connect_form_state import ConnectFormState


@dataclass(frozen=True, slots=True)
class ScreenResult:
    request_quit: bool = False
    next_state: ClientState | None = None
    client_action: object | None = None
    next_connect_form: ConnectFormState | None = None
    connect_requested: bool = False


NO_SCREEN_RESULT = ScreenResult()
