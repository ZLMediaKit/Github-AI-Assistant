# -*- coding:utf-8 -*-
__author__ = 'alex'

# 设置日志
import logging.config
import os
import re
import sys
from logging.handlers import TimedRotatingFileHandler
from typing import Dict, Any

from rich.logging import RichHandler

from core import settings


class NoEscapeSeqFormatter(logging.Formatter):
    def format(self, record):
        message = super().format(record)
        return re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', message)


LOGGING_CONFIG_DEFAULTS: Dict[str, Any] = dict(  # no cov
    version=1,
    disable_existing_loggers=False,
    loggers={
        "sanic.root": {"level": "INFO", "handlers": ["console", "file"]},
        "sanic.error": {
            "level": "INFO",
            "handlers": ["error_console", "file"],
            "propagate": True,
            "qualname": "sanic.error",
        },
        "sanic.access": {
            "level": "INFO",
            "handlers": ["access_console", "file"],
            "propagate": True,
            "qualname": "sanic.access",
        },
        "sanic.server": {
            "level": "INFO",
            "handlers": ["console", "file"],
            "propagate": True,
            "qualname": "sanic.server",
        },
    },
    handlers={
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": sys.stdout,
        },
        "error_console": {
            "class": "logging.StreamHandler",
            "formatter": "generic",
            "stream": sys.stderr,
        },
        "access_console": {
            "class": "logging.StreamHandler",
            "formatter": "access",
            "stream": sys.stdout,
        },
        "file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "formatter": "no_color",
            "filename": "logs/server.log",
            "when": "D",
            "interval": 1,
            "backupCount": 3,
            "encoding": "utf-8",
        },
    },
    formatters={
        "generic": {
            "format": "%(asctime)s [%(process)s] [%(levelname)s] %(message)s",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter",
        },
        "access": {
            "format": "%(asctime)s - (%(name)s)[%(levelname)s][%(host)s]: "
                      + "%(request)s %(message)s %(status)s %(byte)s",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "logging.Formatter",
        },
        "no_color": {
            "format": "%(asctime)s [%(process)s] [%(levelname)s] %(message)s",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "core.log.NoEscapeSeqFormatter",
        },
    },
)


logger = logging.getLogger("default")
if settings.DEBUG:
    logger_level = logging.DEBUG
else:
    logger_level = logging.INFO

logger.setLevel(logger_level)
log_path = os.path.join(settings.BASE_PATH, 'logs')
if not os.path.exists(log_path):
    os.makedirs(log_path)
log_file = os.path.join(log_path, 'app.log')
fh = TimedRotatingFileHandler(log_file, when="D", interval=1, backupCount=3)
fh.setLevel(logger_level)

ch = RichHandler(rich_tracebacks=True, markup=True)
ch.setLevel(logger_level)

formatter = NoEscapeSeqFormatter("%(asctime)s [%(process)s] [%(levelname)s] %(message)s",
                                 datefmt="[%Y-%m-%d %H:%M:%S %z]")
fh.setFormatter(formatter)
ch.setFormatter(logging.Formatter("%(message)s",
                                  datefmt="[%Y-%m-%d %H:%M:%S %z]"))


class VerbosityFilter(logging.Filter):
    verbosity: int = 0

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name.startswith("sanic."):
            return False
        verbosity = getattr(record, "verbosity", 0)
        return verbosity <= self.verbosity


_verbosity_filter = VerbosityFilter()

logger.addHandler(fh)
logger.addHandler(ch)

