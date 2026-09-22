from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def default_log_directory() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    return root / "BaijiuDrink" / "AnfuReportWorkbench" / "logs"


def configure_logging(log_directory: Path | None = None) -> Path:
    directory = Path(log_directory) if log_directory else default_log_directory()
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / "application.log"
    root = logging.getLogger()
    if not any(getattr(handler, "_anfu_handler", False) for handler in root.handlers):
        handler = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler._anfu_handler = True
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s",
                "%Y-%m-%d %H:%M:%S",
            )
        )
        root.addHandler(handler)
        root.setLevel(logging.INFO)
    return log_path
