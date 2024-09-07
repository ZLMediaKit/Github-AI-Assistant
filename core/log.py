# -*- coding:utf-8 -*-
__author__ = 'alex'

# 设置日志
import logging.config
import os
import re
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Dict, Any

from rich.console import Console
from rich.logging import RichHandler

from core import settings


class NoEscapeSeqFormatter(logging.Formatter):
    TAG_RE = re.compile(r'\[([a-z/@]*)]')

    def remove_tags(self, text):
        tags = self.TAG_RE.findall(text)
        for tag in set(tags):
            if tag.startswith('/') or f'/{tag}' in tags:
                text = text.replace(f'[{tag}]', '')
        return text

    def format(self, record):
        message = super().format(record)
        message = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', message)
        return self.remove_tags(message)


class ColoredFormatter(logging.Formatter):
    TAG_RE = re.compile(r'\[([a-z/@]*)]')

    def format(self, record):
        if self.TAG_RE.search(record.msg):
            return super().format(record)
        # 根据日志级别添加颜色标签
        if record.levelno >= logging.ERROR:
            record.msg = f'[red]{record.msg}[/red]'
        elif record.levelno == logging.WARNING:
            record.msg = f'[yellow]{record.msg}[/yellow]'
        return super().format(record)


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
        "access_file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "formatter": "no_color_access",
            "filename": "logs/server.log",
            "when": "D",
            "interval": 1,
            "backupCount": 3,
            "encoding": "utf-8",
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
        "no_color_access": {
            "format": "%(asctime)s - (%(name)s)[%(levelname)s][%(host)s]: %(request)s %(message)s %(status)d %(byte)d",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "core.log.NoEscapeSeqFormatter",
        },
        "no_color": {
            "format": "%(asctime)s [%(process)s] [%(levelname)s] [%(filename)s:%(lineno)s]  %(message)s",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
            "class": "core.log.NoEscapeSeqFormatter",
        },
    },
)


class VerbosityFilter(logging.Filter):
    verbosity: int = 0

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name.startswith("sanic."):
            return False
        verbosity = getattr(record, "verbosity", 0)
        return verbosity <= self.verbosity


_verbosity_filter = VerbosityFilter()
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

ch = RichHandler(console=Console(), rich_tracebacks=True, markup=True, locals_max_length=0,
                 locals_max_string=0)
ch.setLevel(logger_level)

formatter = NoEscapeSeqFormatter("%(asctime)s [%(process)s] [%(levelname)s] %(message)s",
                                 datefmt="[%Y-%m-%d %H:%M:%S %z]")
fh.setFormatter(formatter)
ch.setFormatter(logging.Formatter("%(message)s",
                                  datefmt="[%Y-%m-%d %H:%M:%S %z]"))
logger.addHandler(fh)
logger.addHandler(ch)
