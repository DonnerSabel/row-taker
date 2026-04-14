from __future__ import annotations

import logging
import os
from typing import Final

_LOG_FORMAT: Final[str] = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
_DATE_FORMAT: Final[str] = "%Y-%m-%d %H:%M:%S"
_DEFAULT_LEVEL: Final[str] = "INFO"
_ENV_NAME: Final[str] = "ROW_TAKER_LOG_LEVEL"


def configure_logging(level: str | None = None, *, default: str = _DEFAULT_LEVEL) -> str:
    resolved = (level or os.getenv(_ENV_NAME) or default).upper()
    numeric_level = getattr(logging, resolved, None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"invalid log level: {resolved!r}")
    logging.basicConfig(level=numeric_level, format=_LOG_FORMAT, datefmt=_DATE_FORMAT, force=True)
    return resolved
