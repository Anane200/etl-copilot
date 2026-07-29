"""Centralised logging setup.

Configures the *root* logger once (idempotently) so every module can grab a
child logger with ``logging.getLogger(__name__)`` and inherit handlers, rather
than each module attaching its own handlers (which causes duplicate output).
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

_CONFIGURED = False


def setup_logging(level: int = logging.INFO, log_dir: str | Path = "logs") -> logging.Logger:
    """Configure the root logger with console + timestamped file handlers.

    Safe to call multiple times; only the first call attaches handlers.
    Returns the root logger for convenience.
    """
    global _CONFIGURED
    root = logging.getLogger()
    if _CONFIGURED:
        return root

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"{stamp}.log"

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    _CONFIGURED = True
    root.debug("Logging configured; writing to %s", log_file)
    return root
