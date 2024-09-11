# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
__author__ = 'alex'

import json
import logging
import os

from core import constants
from core.console import console
from core.models import ModelSettings
from core.utils import env
from core.utils.asyncio_utls import ApiLimiter

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

MODELS = json.loads(open(os.path.join(BASE_PATH, './data/models.json'), "r").read())

API_LIMITER = ApiLimiter()

TRANSLATION_MODEL = ModelSettings()
REVIEW_MODEL = ModelSettings()


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


def get_target_lang():
    return get_setting_from_cache(constants.ENV_TRANSLATION_TARGET_LANG, "English")


def get_github_token():
    return get_setting_from_cache(constants.ENV_GITHUB_TOKEN)


def get_secret_key():
    return get_setting_from_cache(constants.ENV_SECRET_KEY)


def get_proxy_url():
    return get_setting_from_cache(constants.ENV_PROXY_URL)


def get_webhook_listen_host():
    return env.get_env(constants.ENV_WEB_HOOK_LISTEN_HOST, "0.0.0.0")


def get_webhook_listen_port():
    return env.get_env(constants.ENV_WEB_HOOK_LISTEN_PORT, 8000)


def get_translator():
    return get_setting_from_cache(constants.ENV_TRANSLATOR, "AdvancedGFMTranslator")


def get_translation_api_limiter():
    return API_LIMITER.get_limiter(TRANSLATION_MODEL.api_key)


def get_review_api_limiter():
    return API_LIMITER.get_limiter(REVIEW_MODEL.api_key)


def get_api_limiter(key: str):
    return API_LIMITER.get_limiter(key)


def init_translation_model(need_model=False):
    translation_model = get_setting_from_cache(constants.ENV_TRANSLATION_MODEL, "gemini/gemini-1.5-flash")
    model_info = MODELS.get(translation_model, None)
    if model_info is None:
        if need_model:
            raise Exception(f"model {translation_model} not found")
        else:
            print(f"model {translation_model} not found, disable translation")
            return
    TRANSLATION_MODEL.model_name = translation_model.split("/")[-1]
    TRANSLATION_MODEL.api_key = get_setting_from_cache(constants.ENV_TRANSLATION_API_KEY)
    TRANSLATION_MODEL.api_url = get_setting_from_cache(constants.ENV_TRANSLATION_API_URL)
    TRANSLATION_MODEL.api_request_limit = get_setting_from_cache(constants.ENV_TRANSLATION_API_REQUEST_LIMIT, 10)
    TRANSLATION_MODEL.max_input_tokens = get_setting_from_cache(constants.ENV_TRANSLATION_API_MAX_INPUT_TOKENS,
                                                                model_info.get("max_input_tokens", 1024 * 4))
    TRANSLATION_MODEL.max_output_tokens = get_setting_from_cache(constants.ENV_TRANSLATION_API_MAX_OUTPUT_TOKENS,
                                                                 model_info.get("max_output_tokens", 8192))
    TRANSLATION_MODEL.provider = model_info.get("provider", "openai_rest")
    TRANSLATION_MODEL.mode = model_info.get("mode", "chat")
    if not TRANSLATION_MODEL.api_key:
        console.print(f"Warning: {constants.ENV_TRANSLATION_API_KEY} is not set", style="bold red")
        return False
    API_LIMITER.add_limiter_by_limit(TRANSLATION_MODEL.api_key, TRANSLATION_MODEL.api_request_limit)


def init_review_model(need_model=False):
    review_model = get_setting_from_cache(constants.ENV_REVIEW_MODEL, None)
    model_info = MODELS.get(review_model, None)
    if model_info is None:
        if need_model:
            raise Exception(f"model {review_model} not found")
        else:
            print(f"model {review_model} not found, disable review")
            return
    REVIEW_MODEL.model_name = review_model.split("/")[-1]
    REVIEW_MODEL.api_key = get_setting_from_cache(constants.ENV_REVIEW_API_KEY)
    REVIEW_MODEL.api_url = get_setting_from_cache(constants.ENV_REVIEW_API_URL)
    REVIEW_MODEL.api_request_limit = get_setting_from_cache(constants.ENV_REVIEW_API_REQUEST_LIMIT, 10)
    REVIEW_MODEL.max_input_tokens = get_setting_from_cache(constants.ENV_REVIEW_API_MAX_INPUT_TOKENS,
                                                           model_info.get("max_input_tokens", 1024 * 4))
    REVIEW_MODEL.max_output_tokens = get_setting_from_cache(constants.ENV_REVIEW_API_MAX_OUTPUT_TOKENS,
                                                            model_info.get("max_output_tokens", 8192))
    REVIEW_MODEL.provider = model_info.get("provider", "openai_rest")
    REVIEW_MODEL.mode = model_info.get("mode", "chat")
    if not REVIEW_MODEL.api_key:
        console.print(f"Warning: {constants.ENV_REVIEW_API_KEY} is not set", style="bold red")
        return False
    API_LIMITER.add_limiter_by_limit(REVIEW_MODEL.api_key, REVIEW_MODEL.api_request_limit)


def setup_translation_env(github_token: str, model_name: str, api_key: str, api_url=None, proxy_url=None):
    if not setup_base_env(github_token, model_name, proxy_url):
        return False
    if model_name:
        env.set_env(constants.ENV_TRANSLATION_MODEL, model_name)

    if api_key:
        env.set_env(constants.ENV_TRANSLATION_API_KEY, api_key)
    if api_url:
        env.set_env(constants.ENV_TRANSLATION_API_URL, api_url)
    if not env.get_env(constants.ENV_TRANSLATION_API_KEY):
        console.print(f"Warning: {constants.ENV_TRANSLATION_API_KEY} is not set", style="bold red")
        return False
    init_translation_model()
    return True


def setup_review_env(github_token: str, model_name: str, api_key: str, api_url=None, proxy_url=None):
    if not setup_base_env(github_token, model_name, proxy_url):
        return False
    if model_name:
        env.set_env(constants.ENV_REVIEW_MODEL, model_name)
    if api_key:
        env.set_env(constants.ENV_REVIEW_API_KEY, api_key)
    if api_url:
        env.set_env(constants.ENV_REVIEW_API_URL, api_url)
    if not env.get_env(constants.ENV_REVIEW_API_KEY):
        console.print(f"Warning: {constants.ENV_REVIEW_API_KEY} is not set", style="bold red")
        return False
    init_translation_model()
    return True


def setup_base_env(github_token: str, model_name: str, proxy_url=None) -> bool:
    setup_github_token(github_token)
    if model_name and model_name not in MODELS:
        print(f"model_name {model_name} not in {MODELS}")
        return False
    if proxy_url:
        env.set_env(constants.ENV_PROXY_URL, proxy_url)
    return True
