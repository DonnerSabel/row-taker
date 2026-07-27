from __future__ import annotations

from row_taker.gui_workbench.main import _parse_frames, _parse_point, _parse_size, run


def test_workbench_cli_value_parsers() -> None:
    assert _parse_size("1600x900") == (1600, 900)
    assert _parse_point("123,456") == (123, 456)
    assert _parse_frames("0,8,16,32") == (0, 8, 16, 32)


def test_workbench_list_command(capsys) -> None:
    assert run(["--list"]) == 0

    output = capsys.readouterr().out
    assert "choose-card" in output
    assert "overflow-resolved" in output
    assert "frames: 0,8,16,24,32" in output


def test_workbench_timeline_list_command(capsys) -> None:
    assert run(["--list-timelines"]) == 0

    output = capsys.readouterr().out
    assert "full-trick" in output
    assert "PresentationRowChosen" in output
    assert "steps: 11" in output
