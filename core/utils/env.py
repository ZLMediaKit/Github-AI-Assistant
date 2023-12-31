# -*- coding:utf-8 -*-
__author__ = 'alex'

import os
import dotenv

default_env_path = [dotenv.find_dotenv()]


def load_env(env_path=None):
    """
    load env from .env file
    :param env_path:
    :return:
    """
    if not env_path:
        env_path = dotenv.find_dotenv()
    default_env_path[0] = env_path
    dotenv.load_dotenv(env_path)


def get_env(key, default=None):
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

