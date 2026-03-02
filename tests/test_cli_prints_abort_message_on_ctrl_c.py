# tests/test_ctrl_c_unit.py
import builtins

from _pytest.capture import CaptureFixture
from _pytest.monkeypatch import MonkeyPatch

import row_taker.cli.main as m


def test_cli_prints_abort_message_on_ctrl_c(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    def raise_ctrl_c(prompt: str = "") -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr(builtins, "input", raise_ctrl_c)

    exit_code = m.run()

    out = capsys.readouterr().out
    assert "Abbruch" in out
    assert exit_code == 0
