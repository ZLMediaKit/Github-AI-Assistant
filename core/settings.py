# -*- coding:utf-8 -*-
__author__ = 'alex'

import os

import openai


from core import constants
from core.console import console
from core.utils import env

env.load_env()
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PID_FILE = "/tmp/translation/run/server.pid"
DEBUG = env.get_env(constants.ENV_DEBUG, True)


def setup_github_token(token):
    if token is not None:
        env.set_env(constants.ENV_GITHUB_TOKEN, token)
    if env.get_env(constants.ENV_GITHUB_TOKEN) is None:
        raise Exception(f"{constants.ENV_GITHUB_TOKEN} is not set")


def setup_openai(key, proxy):
    if key is not None:
        env.set_env(constants.ENV_OPENAI_KEY, key)
    if proxy is not None:
        env.set_env(constants.ENV_OPENAI_PROXY, proxy)
    if env.get_env(constants.ENV_OPENAI_KEY) is None:
        raise Exception(f"{constants.ENV_OPENAI_KEY} is not set")

    openai.api_key = env.get_env(constants.ENV_OPENAI_KEY)
    if env.get_env(constants.ENV_OPENAI_PROXY) is not None:
        openai.api_base = "http://" + env.get_env(constants.ENV_OPENAI_PROXY) + "/v1/"
    else:
        console.print(f"Warning: {constants.ENV_OPENAI_PROXY} is not set")


def setup_gemini_api_key(key):
    if key is not None:
        env.set_env(constants.ENV_GEMINI_KEY, key)
    if env.get_env(constants.ENV_GEMINI_KEY) is None:
        raise Exception(f"{constants.ENV_GEMINI_KEY} is not set")
    return env.get_env(constants.ENV_GEMINI_KEY)


def get_gemini_api_key():
    return env.get_env(constants.ENV_GEMINI_KEY)


def get_secret_key():
    return env.get_env(constants.ENV_SECRET_KEY)


def setup_env(github_token, openai_key, openai_proxy, gemini_key, secret_key=None):
    setup_github_token(github_token)
    if openai_key:
        setup_openai(openai_key, openai_proxy)
    if gemini_key:
        setup_gemini_api_key(gemini_key)
    if secret_key:
        env.set_env(constants.ENV_SECRET_KEY, secret_key)
    if not openai.api_key and not get_gemini_api_key():
        console.print(f"Warning: {constants.ENV_OPENAI_KEY} and {constants.ENV_GEMINI_KEY} are not set",
                      style="bold red")
        return False
    return True
