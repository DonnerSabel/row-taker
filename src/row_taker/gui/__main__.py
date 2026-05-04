import sys

# Standard: Lobby-GUI starten
# Mit --demo: altes Spielfeld-Demo starten
if "--demo" in sys.argv:
    from row_taker.gui.main import run
else:
    from row_taker.gui.gui_main import run_lobby as run

raise SystemExit(run())
