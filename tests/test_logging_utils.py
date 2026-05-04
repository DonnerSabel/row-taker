from __future__ import annotations

from pathlib import Path

from row_taker.logging_utils import configure_logging


def test_configure_logging_can_write_to_file(tmp_path: Path) -> None:
    logfile = tmp_path / "client.log"
    configure_logging("DEBUG", log_file=str(logfile))

    import logging

    logger = logging.getLogger("row_taker.test")
    logger.debug("hello log file")

    contents = logfile.read_text(encoding="utf-8")
    assert "hello log file" in contents
