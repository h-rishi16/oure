"""Structured logging configuration using structlog."""

import logging
import sys
from enum import Enum

import structlog


class LogFormat(str, Enum):
    CONSOLE = "console"  # Human-readable (Rich renderer)
    JSON = "json"  # Machine-readable (for log aggregators)


def configure_logging(
    level: str = "INFO",
    format: LogFormat = LogFormat.CONSOLE,
    log_file: str | None = None,
) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    handlers: list[logging.Handler] = []
    handlers.append(logging.StreamHandler(sys.stdout))
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(level=numeric_level, format="%(message)s", handlers=handlers)

    processors: list[structlog.typing.Processor] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if format == LogFormat.JSON:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
