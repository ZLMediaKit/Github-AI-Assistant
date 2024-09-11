# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
__author__ = 'alex'

import logging.config
import os
import re
import sys
from pathlib import Path
from typing import Dict, Any

from rich.console import Console

PROJECT_BASE_PATH = BASE_DIR = Path(__file__).resolve().parent.parent


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
        "default": {
            "level": "INFO",
            "handlers": ["rich_console", "file"],
            "propagate": False,
        },
        "sanic.root": {
            "level": "INFO",
            "handlers": ["console", "file"]},
        "sanic.error": {
            "level": "INFO",
            "handlers": ["error_console", "file"],
            "propagate": True,
            "qualname": "sanic.error",
        },
        "sanic.access": {
            "level": "INFO",
            "handlers": ["access_console", "access_file"],
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
        "rich_console": {
            "class": "rich.logging.RichHandler",
            "formatter": "rich_formatter",
            "console": Console(),
            "rich_tracebacks": True,
            "markup": True,
            "locals_max_length": 0,
            "locals_max_string": 0,
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
        "rich_formatter": {
            "format": "%(message)s",
            "datefmt": "[%Y-%m-%d %H:%M:%S %z]",
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


def init_logging(app_name: str, logger_path: str = None, logger_level: int = logging.INFO) -> None:
    """
    Initialize logging defaults for Project.
    :param app_name:
    :param logger_level:
    :param logger_path:
    """
    # Set the level for all loggers
    for define_logger in LOGGING_CONFIG_DEFAULTS["loggers"].values():
        define_logger["level"] = logger_level
    if not logger_path:
        logger_path = os.path.join(PROJECT_BASE_PATH, 'logs')
    if not os.path.exists(logger_path):
        os.makedirs(logger_path)

    log_file_prefix = app_name.lower().strip().replace(" ", "_")
    log_file_path = os.path.join(logger_path, f'{log_file_prefix}.log')
    log_access_file_path = os.path.join(logger_path, f'{log_file_prefix}_access.log')
    LOGGING_CONFIG_DEFAULTS["handlers"]["file"]["filename"] = log_file_path
    LOGGING_CONFIG_DEFAULTS["handlers"]["access_file"]["filename"] = log_access_file_path
    print(f"The log file is: {log_file_path}")
    print(f"The access log file is: {log_access_file_path}")
    logging.config.dictConfig(LOGGING_CONFIG_DEFAULTS)
    logger.setLevel(logger_level)
