# Copyright (c) 2010-2025 Evolveum and contributors
#
# Licensed under the EUPL-1.2 or later.

import logging
import sys
from contextvars import ContextVar

from colorlog import ColoredFormatter

from src.config import config

request_id: ContextVar[str] = ContextVar("request_id", default="-")


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        return True


def setup_logging():
    """
    Configure the root logger and Hypercorn loggers based on application settings.
    """
    level = getattr(logging, config.logging.level.value.upper(), logging.INFO)

    # Base logger config
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | request_id=%(request_id)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if not any(isinstance(f, RequestContextFilter) for f in handler.filters):
            handler.addFilter(RequestContextFilter())

    if config.logging.colors:
        color_formatter = ColoredFormatter(
            "%(log_color)s%(asctime)s | %(levelname)-8s | %(name)s | request_id=%(request_id)s | %(message)s",
            datefmt=None,
            reset=True,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        )
        for handler in root_logger.handlers:
            handler.setFormatter(color_formatter)

    hypercorn_access = logging.getLogger("hypercorn.access")
    hypercorn_error = logging.getLogger("hypercorn.error")

    hypercorn_access.setLevel(level)
    hypercorn_error.setLevel(level)

    logging.getLogger("openai").setLevel(logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.INFO)
