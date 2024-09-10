# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/translation_issues).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
__author__ = 'alex'

import logging
import os

import openai

from core import constants
from core.console import console
from core.utils import env

env.load_env()
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PID_FILE = "/tmp/translation/run/server.pid"
CACHE_SETTINGS = {}
DEBUG = env.get_env(constants.ENV_DEBUG, True)
AUTO_RELOAD = env.get_env(constants.ENV_AUTO_RELOAD, DEBUG)
WEB_HOOK_WORKERS = env.get_env(constants.ENV_WEB_HOOK_WORKERS, 1)
WEB_HOOK_ACCESS_LOG = env.get_env(constants.ENV_WEB_HOOK_ACCESS_LOG, DEBUG)

MEDIA_ROOT = os.path.join(BASE_PATH, '../media')
MEDIA_URL = '/media/'

STATIC_ROOT = os.path.join(BASE_PATH, 'static')
STATIC_URL = 'static/'

if DEBUG:
    LOGGER_LEVEL = logging.DEBUG
else:
    LOGGER_LEVEL = logging.INFO


def get_setting_from_cache(key, default=None):
    cache_value = CACHE_SETTINGS.get(key, None)
    if cache_value is None:
        cache_value = env.get_env(key, default)
        CACHE_SETTINGS[key] = cache_value
    return cache_value


def setup_github_token(token):
    if token is not None:
        env.set_env(constants.ENV_GITHUB_TOKEN, token)
    if env.get_env(constants.ENV_GITHUB_TOKEN) is None:
        raise Exception(f"{constants.ENV_GITHUB_TOKEN} is not set")


def setup_openai(key, proxy):
    if key is not None:
        env.set_env(constants.ENV_OPENAI_KEY, key)
    if proxy is not None:
        env.set_env(constants.ENV_OPENAI_URL, proxy)
    if env.get_env(constants.ENV_OPENAI_KEY) is None:
        raise Exception(f"{constants.ENV_OPENAI_KEY} is not set")

    openai.api_key = env.get_env(constants.ENV_OPENAI_KEY)
    openai_url = env.get_env(constants.ENV_OPENAI_URL)
    if openai_url is not None:
        openai.api_base = openai_url
    else:
        console.print(f"Warning: {constants.ENV_OPENAI_URL} is not set")


def setup_gemini_api_key(key):
    if key is not None:
        env.set_env(constants.ENV_GEMINI_KEY, key)
    if env.get_env(constants.ENV_GEMINI_KEY) is None:
        raise Exception(f"{constants.ENV_GEMINI_KEY} is not set")
    return env.get_env(constants.ENV_GEMINI_KEY)


def get_github_token():
    return get_setting_from_cache(constants.ENV_GITHUB_TOKEN)


def get_gemini_api_key():
    return get_setting_from_cache(constants.ENV_GEMINI_KEY)


def get_secret_key():
    return get_setting_from_cache(constants.ENV_SECRET_KEY)


def get_proxy_url():
    return get_setting_from_cache(constants.ENV_PROXY_URL)


def get_webhook_listen_host():
    return env.get_env(constants.ENV_WEB_HOOK_LISTEN_HOST, "0.0.0.0")


def get_webhook_listen_port():
    return env.get_env(constants.ENV_WEB_HOOK_LISTEN_PORT, 8000)


def get_gpt_model():
    return get_setting_from_cache(constants.ENV_GPT_MODEL, "gpt-4-1106-preview")


def get_gemini_model():
    return get_setting_from_cache(constants.ENV_GEMINI_MODEL, "gemini-1.5-flash")


def get_api_request_limit():
    return get_setting_from_cache(constants.ENV_API_REQUEST_LIMIT, 10)


def get_max_tokens():
    return get_setting_from_cache(constants.ENV_MAX_TOKENS, 8096)


def get_translator():
    return get_setting_from_cache(constants.ENV_TRANSLATOR, "AdvancedGFMTranslator")


def setup_env(github_token, openai_key, openai_url, gemini_key, proxy_url=None):
    setup_github_token(github_token)
    if openai_key:
        setup_openai(openai_key, openai_url)
    if gemini_key:
        setup_gemini_api_key(gemini_key)
    if proxy_url:
        env.set_env(constants.ENV_PROXY_URL, proxy_url)
    if not openai.api_key and not get_gemini_api_key():
        console.print(f"Warning: {constants.ENV_OPENAI_KEY} and {constants.ENV_GEMINI_KEY} are not set",
                      style="bold red")
        return False
    return True
