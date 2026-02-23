# tests/test_ctrl_c_unit.py
import builtins
import importlib

import pytest
from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch


def test_cli_prints_abort_message_on_ctrl_c(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    def raise_ctrl_c(prompt: str = "") -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr(builtins, "input", raise_ctrl_c)

    import row_taker.cli.main as m

    importlib.reload(m)

    with pytest.raises(SystemExit):
        m.main()

    out: builtins.str = capsys.readouterr().out
    assert "Abbruch" in out
