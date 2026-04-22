from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ConnectFormState:
    host: str = '127.0.0.1'
    port: str = '8765'
    display_name: str = 'Spieler'
    active_field: str = 'display_name'
    error_message: str | None = None
    status_message: str = 'Enter verbindet. Tab wechselt zum nächsten Feld.'


__all__ = ['ConnectFormState']
