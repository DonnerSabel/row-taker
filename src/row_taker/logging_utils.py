from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Final

_LOG_FORMAT: Final[str] = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
_DEFAULT_LEVEL: Final[str] = "INFO"
_ENV_NAME: Final[str] = "ROW_TAKER_LOG_LEVEL"


def configure_logging(
    level: str | None = None,
    *,
    default: str = _DEFAULT_LEVEL,
    log_file: str | None = None,
) -> str:
    resolved = (level or os.getenv(_ENV_NAME) or default).upper()
    numeric_level = getattr(logging, resolved, None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"invalid log level: {resolved!r}")

    handlers: list[logging.Handler]
    if log_file:
        path = Path(log_file).expanduser()
        if path.parent != Path('.'):
            path.parent.mkdir(parents=True, exist_ok=True)
        handlers = [logging.FileHandler(path, encoding='utf-8')]
    else:
        handlers = [logging.StreamHandler()]

    logging.basicConfig(
        level=numeric_level,
        format=_LOG_FORMAT,
        datefmt=_DATE_FORMAT,
        force=True,
        handlers=handlers,
    )
    return resolved
