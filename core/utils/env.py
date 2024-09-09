# -*- coding:utf-8 -*-
__author__ = 'alex'

import os
from typing import Any

import dotenv

from core.console import console
from core.utils import strings

default_env_path = [dotenv.find_dotenv()]


def load_env(env_path: str = None):
    """
    load env from .env file
    :param env_path:
    :return:
    """
    if not env_path:
        env_path = dotenv.find_dotenv()
    default_env_path[0] = env_path
    dotenv.load_dotenv(env_path)


def get_env(key: str, default=None) -> bool | int | str | float | Any:
    """
    get env value
    :param key:
    :param default:
    :return:
    """
    value = os.environ.get(key, default)
    if isinstance(value, str):
        if value.lower() == "true":
            return True
        elif value.lower() == "false":
            return False
    if isinstance(value, str):
        if value.isdigit():
            return int(value)
        # 判断是否是ip地址
        elif strings.is_ip_address(value):
            return value
        elif value.replace(".", "").isdigit():
            return float(value)
    return value


def set_env(key, value, update_env_file=False):
    """
    set env value
    :param update_env_file:
    :param key:
    :param value:
    :return:
    """
    if isinstance(value, bool):
        value = str(value).lower()
    if not isinstance(value, str):
        value = str(value)
    os.environ[key] = value
    if update_env_file:
        dotenv.set_key(default_env_path[0], key, value)


def update_env(key, value):
    """
    update env value
    :param key:
    :param value:
    :return:
    """
    old_value = get_env(key)
    if value != old_value:
        set_env(key, value, True)
        console.print(f"update {key} from {old_value} to {value}")
