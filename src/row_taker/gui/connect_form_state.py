from __future__ import annotations

from dataclasses import dataclass


DEFAULT_CONNECT_FIELDS = ("host", "port", "display_name")


@dataclass(frozen=True, slots=True)
class ConnectFormState:
    host: str = "127.0.0.1"
    port: str = "8765"
    display_name: str = "Spieler"
    active_field: str = "display_name"
    error_message: str | None = None
    status_message: str = "Tab nächstes Feld · Enter verbinden · Esc beenden"
    auto_select_fields: tuple[str, ...] = DEFAULT_CONNECT_FIELDS
    selected_field: str | None = "display_name"


__all__ = ["ConnectFormState", "DEFAULT_CONNECT_FIELDS"]
