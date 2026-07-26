"""Logging helpers for ND-Hub desktop entry (Issue #93)."""
from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def build_logging_handlers(config) -> list:
    """Erzeugt Logging-Handler mit robuster Fallback-Strategie."""
    handlers: list = [logging.StreamHandler()]
    try:
        log_dir = config.get_log_dir()
        os.makedirs(log_dir, exist_ok=True)
        handlers.insert(
            0,
            RotatingFileHandler(
                os.path.join(log_dir, "nd_hub.log"),
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            ),
        )
    except Exception as exc:
        sys.stderr.write(f"Warnung: Dateilogging deaktiviert ({exc})\n")
    return handlers


def configure_app_logging(config) -> tuple[logging.Logger, logging.Logger]:
    """Configure root ND-Hub + perf loggers. Returns (logger, perf_logger)."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=build_logging_handlers(config),
    )
    logger = logging.getLogger("ND-Hub")
    perf_logger = logging.getLogger("perf")
    perf_log_path = os.path.join(config.get_log_dir(), "nd_hub_perf.log")
    try:
        os.makedirs(config.get_log_dir(), exist_ok=True)
        perf_handler = RotatingFileHandler(
            perf_log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        perf_handler.setLevel(logging.DEBUG)
        perf_logger.addHandler(perf_handler)
    except Exception as exc:
        logger.debug("Perf-File-Logger deaktiviert: %s", exc)
    perf_logger.setLevel(logging.DEBUG)
    return logger, perf_logger
