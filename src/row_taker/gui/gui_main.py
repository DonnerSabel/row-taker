"""Startet die grafische Lobby-Oberfläche von RowTaker."""

from __future__ import annotations


def run_lobby() -> int:
    """Öffnet das Lobby-Fenster. Gibt Exit-Code zurück."""
    from row_taker.gui.lobby import LobbyWindow

    window = LobbyWindow()
    return window.run()


def main() -> None:
    raise SystemExit(run_lobby())


if __name__ == "__main__":
    main()
