# -*- coding:utf-8 -*-

#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#

"""
@author:alex
@date:2024/9/11
@time:下午4:40
"""
__author__ = 'alex'

from rich.prompt import Confirm, Prompt, IntPrompt

from core import constants, settings
from core.console import console, select_prompt
from core.utils import env


def update_env():
    enable_debug = Confirm.ask("Enable debug mode?",
                               console=console,
                               default=env.get_env(constants.ENV_DEBUG))
    env.update_env(constants.ENV_DEBUG, enable_debug)
    translation_target_lang_ask = Prompt.ask("Please enter the language you would like to translate into?",
                                             console=console,
                                             default=env.get_env(constants.ENV_TRANSLATION_TARGET_LANG, "English"))
    env.update_env(constants.ENV_TRANSLATION_TARGET_LANG, translation_target_lang_ask)
    github_token_ask = Prompt.ask("Please input your github token",
                                  console=console,
                                  default=env.get_env(constants.ENV_GITHUB_TOKEN))
    env.update_env(constants.ENV_GITHUB_TOKEN, github_token_ask)

    github_username_ask = Prompt.ask("Please input your github username",
                                     console=console,
                                     default=env.get_env(constants.ENV_GITHUB_USERNAME))
    env.update_env(constants.ENV_GITHUB_USERNAME, github_username_ask)
    secret_key_ask = Prompt.ask("Please input your github webhook secret key",
                                console=console,
                                default=env.get_env(constants.ENV_SECRET_KEY))
    env.update_env(constants.ENV_SECRET_KEY, secret_key_ask)

    proxy_url_ask = Prompt.ask("Please input your proxy url, leave none if not use proxy for ai api",
                               console=console,
                               default=env.get_env(constants.ENV_PROXY_URL))
    env.update_env(constants.ENV_PROXY_URL, proxy_url_ask)

    webhook_listen_host_ask = Prompt.ask("Please input your webhook listen host",
                                         console=console,
                                         default=env.get_env(constants.ENV_WEB_HOOK_LISTEN_HOST, "127.0.0.1"))
    env.update_env(constants.ENV_WEB_HOOK_LISTEN_HOST, webhook_listen_host_ask)
    while True:
        server_port_ask = IntPrompt.ask("Please input your webhook listen port",
                                        console=console,
                                        default=env.get_env(constants.ENV_WEB_HOOK_LISTEN_PORT, 8080))
        if not (0 < server_port_ask < 65535):
            console.print("Server port must be a number and between 0 and 65535", style="bold red")
        else:
            env.update_env(constants.ENV_WEB_HOOK_LISTEN_PORT, server_port_ask)
            break
    auto_reload_ask = Confirm.ask("Enable auto reload?",
                                  console=console,
                                  default=env.get_env(constants.ENV_AUTO_RELOAD))
    env.update_env(constants.ENV_AUTO_RELOAD, auto_reload_ask)
    webhook_workers_ask = IntPrompt.ask("Please input your webhook workers",
                                        console=console,
                                        default=env.get_env(constants.ENV_WEB_HOOK_WORKERS, 1))
    env.update_env(constants.ENV_WEB_HOOK_WORKERS, webhook_workers_ask)
    webhook_access_log_ask = Confirm.ask("Enable webhook access log?",
                                         console=console,
                                         default=env.get_env(constants.ENV_WEB_HOOK_ACCESS_LOG))
    env.update_env(constants.ENV_WEB_HOOK_ACCESS_LOG, webhook_access_log_ask)

    # 提示是否使用翻译服务
    use_translation_service = Confirm.ask("Do you want to use translation service?", console=console)
    if use_translation_service:
        setup_translation_env()
    # 提示是否使用review服务
    use_review_service = Confirm.ask("Do you want to use review service?", console=console)
    if use_review_service:
        setup_review_env()


def setup_translation_env():
    translation_model_ask = select_prompt("Please select your translation model",
                                          settings.MODELS,
                                          default=env.get_env(constants.ENV_TRANSLATION_MODEL))
    env.update_env(constants.ENV_TRANSLATION_MODEL, translation_model_ask)

    translation_api_request_limit_ask = IntPrompt.ask("Please input your translation api request limit",
                                                      console=console,
                                                      default=env.get_env(
                                                          constants.ENV_TRANSLATION_API_REQUEST_LIMIT, 10))
    env.update_env(constants.ENV_TRANSLATION_API_REQUEST_LIMIT, translation_api_request_limit_ask)

    translation_api_key_ask = Prompt.ask("Please input your translation api key",
                                         console=console,
                                         default=env.get_env(constants.ENV_TRANSLATION_API_KEY))
    env.update_env(constants.ENV_TRANSLATION_API_KEY, translation_api_key_ask)

    translation_api_url_ask = Prompt.ask("Please input your translation api url, if use default leave none",
                                         console=console,
                                         default=env.get_env(constants.ENV_TRANSLATION_API_URL))
    env.update_env(constants.ENV_TRANSLATION_API_URL, translation_api_url_ask)

    model_settings = settings.MODELS.get(translation_model_ask)
    translation_api_max_input_tokens_ask = IntPrompt.ask("Please input your translation api max input tokens, "
                                                         "if use default leave none",
                                                         console=console,
                                                         default=env.get_env(
                                                             constants.ENV_TRANSLATION_API_MAX_INPUT_TOKENS,
                                                             model_settings.get("max_input_tokens", 1024 * 4)))
    env.update_env(constants.ENV_TRANSLATION_API_MAX_INPUT_TOKENS, translation_api_max_input_tokens_ask)

    translation_api_max_output_tokens_ask = IntPrompt.ask("Please input your translation api max output tokens, "
                                                          "if use default leave none",
                                                          console=console,
                                                          default=env.get_env(
                                                              constants.ENV_TRANSLATION_API_MAX_OUTPUT_TOKENS,
                                                              model_settings.get("max_output_tokens", 8192)))
    env.update_env(constants.ENV_TRANSLATION_API_MAX_OUTPUT_TOKENS, translation_api_max_output_tokens_ask)


def setup_review_env():
    review_model_ask = select_prompt("Please select your review model",
                                     settings.MODELS,
                                     default=env.get_env(constants.ENV_REVIEW_MODEL))
    env.update_env(constants.ENV_REVIEW_MODEL, review_model_ask)

    review_api_request_limit_ask = IntPrompt.ask("Please input your review api request limit",
                                                 console=console,
                                                 default=env.get_env(constants.ENV_REVIEW_API_REQUEST_LIMIT, 10))
    env.update_env(constants.ENV_REVIEW_API_REQUEST_LIMIT, review_api_request_limit_ask)

    review_api_key_ask = Prompt.ask("Please input your review api key",
                                    console=console,
                                    default=env.get_env(constants.ENV_REVIEW_API_KEY))
    env.update_env(constants.ENV_REVIEW_API_KEY, review_api_key_ask)

    review_api_url_ask = Prompt.ask("Please input your review api url, if use default leave none",
                                    console=console,
                                    default=env.get_env(constants.ENV_REVIEW_API_URL))
    env.update_env(constants.ENV_REVIEW_API_URL, review_api_url_ask)
    model_settings = settings.MODELS.get(review_model_ask)
    review_api_max_input_tokens_ask = IntPrompt.ask("Please input your review api max input tokens, "
                                                    "if use default leave none",
                                                    console=console,
                                                    default=env.get_env(
                                                        constants.ENV_REVIEW_API_MAX_INPUT_TOKENS,
                                                        model_settings.get("max_input_tokens", 1024 * 8)))
    env.update_env(constants.ENV_REVIEW_API_MAX_INPUT_TOKENS, review_api_max_input_tokens_ask)

    review_api_max_output_tokens_ask = IntPrompt.ask("Please input your review api max output tokens, "
                                                     "if use default leave none",
                                                     console=console,
                                                     default=env.get_env(
                                                         constants.ENV_REVIEW_API_MAX_OUTPUT_TOKENS,
                                                         model_settings.get("max_output_tokens", 1024 * 8)))
    env.update_env(constants.ENV_REVIEW_API_MAX_OUTPUT_TOKENS, review_api_max_output_tokens_ask)
