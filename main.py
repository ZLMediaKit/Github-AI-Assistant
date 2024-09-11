# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
import asyncio
import os.path
import signal
import sys
from threading import Event

import typer
from rich.progress import (
    Progress,
)
from typing_extensions import Annotated

from apps import trans, review
from core import settings, constants, translate, setup
from core.console import console
from core.log import init_logging
from core.utils import system, systemd

app = typer.Typer(no_args_is_help=True,
                  help="Auto trans issues/pull requests/discussions to english")

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
init_logging("main", logger_path=None, logger_level=settings.LOGGER_LEVEL)

done_event = Event()


def handle_sigint(signum, frame):
    done_event.set()


signal.signal(signal.SIGINT, handle_sigint)


def install_requirements(progress):
    """
    Install requirements
    :param progress:
    :return:
    """
    progress.console.print("Installing requirements", style="bold green")
    try:
        system.run_cmd("pip3 install -r ./requirements.txt", True, True)
        progress.console.print("Install requirements success", style="bold green")
    except Exception:
        progress.console.print("Install requirements fail", style="bold red")
        console.print_exception(show_locals=True)
        sys.exit(1)


def install_panel():
    """
    Install app
    :return:
    """
    installed_flag_file = os.path.join(BASE_PATH, ".installed")
    if os.path.exists(installed_flag_file):
        return
    with Progress() as progress:
        task = progress.add_task("Installing, please wait", total=6)
        install_requirements(progress)
        progress.advance(task)
    console.print("Installed Done!")
    setup.update_env()
    console.print("Update .env file success", style="bold green")
    with open(installed_flag_file, "w") as f:
        f.write("installed")


@app.command("shell", help="Activate the virtual environment")
def cmd():
    """
    After executing this method, the current program exits, but the env is activated, similar to executing source env/bin/activate under shell
    :return:
    """
    os.system("bash")


@app.command("update_env", help="Update .env file")
def update_env():
    """
    update .env file
    :return:
    """
    setup.update_env()
    console.print("Update .env file success", style="bold green")


@app.command("auto_start", help="Auto start when boot")
def auto_start_when_boot(enable: Annotated[bool, typer.Option(help="Enable Auto start when boot")] = False):
    """
    Auto start when boot
    :return:
    """
    systemd.install_startup()
    systemd.auto_start_when_boot(enable)


@app.command("trans_issues", help="Translate a specific issue into english")
def trans_issues(input_url: Annotated[str, typer.Option(help="GitHub issue URL, for example, "
                                                             "https://github.com/your-org/your-repository/issues/1")],
                 github_token: Annotated[str, typer.Option(help="GitHub access token, for example, "
                                                                "github_pat_xxx_yyyyyy",
                                                           envvar=[constants.ENV_GITHUB_TOKEN])],
                 model_name: Annotated[str, typer.Option(
                     help="The name of the AI model, such as gemini/gemini-1.5-flash")] = None,
                 api_url: Annotated[str, typer.Option(
                     help="The request URL of the AI model API. If you use the official API, it is not required.")] = None,
                 api_key: Annotated[str, typer.Option(
                     help="The API key of the model, for example, xxxyyyzzz")] = None,
                 proxy_url: Annotated[str, typer.Option(
                     help="The url of the http proxy used when requesting the model's API, "
                          "for example, http://127.0.0.1:8118")] = None
                 ):
    """
    Translate issues to english
    :return:
    """
    setup_result = settings.setup_translation_env(github_token, model_name, api_url, api_key, proxy_url)
    if not setup_result:
        return
    asyncio.run(trans.trans_issues(input_url))


@app.command("test_translate", help="Test translate")
def test_translate(github_token: Annotated[str, typer.Option(help="GitHub access token, for example, "
                                                                  "github_pat_xxx_yyyyyy",
                                                             envvar=[constants.ENV_GITHUB_TOKEN])],
                   model_name: Annotated[str, typer.Option(
                       help="The name of the AI model, such as gemini/gemini-1.5-flash")] = None,
                   api_url: Annotated[str, typer.Option(
                       help="The request URL of the AI model API. If you use the official API, it is not required.")] = None,
                   api_key: Annotated[str, typer.Option(
                       help="The API key of the model, for example, xxxyyyzzz")] = None,
                   proxy_url: Annotated[str, typer.Option(
                       help="The url of the http proxy used when requesting the model's API, "
                            "for example, http://127.0.0.1:8118")] = None
                   ):
    setup_result = settings.setup_translation_env(github_token, model_name, api_url, api_key, proxy_url)
    if not setup_result:
        return
    console.print("Test translate, the original content is:", style="bold green")
    with open(os.path.join(BASE_PATH, "./test/test_issues.md"), "r") as f:
        md = f.read()
        console.print(md)
        translator = translate.get_translator(settings.get_translator(),
                                              max_tokens=settings.TRANSLATION_MODEL.max_input_tokens)
        translated_body, has_translated_by_gpt, real_translated = asyncio.run(translator.translate(md))
        if translated_body and real_translated:
            console.print("The translated content is:", style="bold green")
            console.print(translated_body)
        else:
            console.print("The translated content is empty", style="bold red")


@app.command("trans_commit", help="Translate a specific commit into english")
def trans_commit(input_url: Annotated[str, typer.Option(
    help="GitHub commit URL, for example, "
         "https://github.com/your-org/your-repository/commit/8768ec2f6bacc204f167ef19f15fb869664d9410")],
                 github_token: Annotated[str, typer.Option(help="GitHub access token, for example, "
                                                                "github_pat_xxx_yyyyyy",
                                                           envvar=[constants.ENV_GITHUB_TOKEN])],
                 model_name: Annotated[str, typer.Option(
                     help="The name of the AI model, such as gemini/gemini-1.5-flash")] = None,
                 api_url: Annotated[str, typer.Option(
                     help="The request URL of the AI model API. If you use the official API, it is not required.")] = None,
                 api_key: Annotated[str, typer.Option(
                     help="The API key of the model, for example, xxxyyyzzz")] = None,
                 proxy_url: Annotated[str, typer.Option(
                     help="The url of the http proxy used when requesting the model's API, "
                          "for example, http://127.0.0.1:8118")] = None
                 ):
    """
    Translate issues to english
    :return:
    """
    setup_result = settings.setup_translation_env(github_token, model_name, api_url, api_key, proxy_url)
    if not setup_result:
        return
    asyncio.run(trans.trans_issues(input_url))


@app.command("trans_discussions", help="Translate a specific discussion into english")
def trans_discussion(input_url: Annotated[str, typer.Option(help="GitHub discussion URL, for example, "
                                                                 "https://github.com/your-org/your-repository/discussions/1")],
                     github_token: Annotated[str, typer.Option(help="GitHub access token, for example, "
                                                                    "github_pat_xxx_yyyyyy",
                                                               envvar=[constants.ENV_GITHUB_TOKEN])],
                     model_name: Annotated[str, typer.Option(
                         help="The name of the AI model, such as gemini/gemini-1.5-flash")] = None,
                     api_url: Annotated[str, typer.Option(
                         help="The request URL of the AI model API. If you use the official API, it is not required.")] = None,
                     api_key: Annotated[str, typer.Option(
                         help="The API key of the model, for example, xxxyyyzzz")] = None,
                     proxy_url: Annotated[str, typer.Option(
                         help="The url of the http proxy used when requesting the model's API, "
                              "for example, http://127.0.0.1:8118")] = None
                     ):
    """
    Translate issues to english
    :return:
    """
    setup_result = settings.setup_translation_env(github_token, model_name, api_url, api_key, proxy_url)
    if not setup_result:
        return
    asyncio.run(trans.trans_discussion(input_url))


@app.command("trans_pr", help="Translate a specific PR into english")
def trans_pr(input_url: Annotated[str, typer.Option(help="GitHub PR URL, for example, "
                                                         "https://github.com/your-org/your-repository/pull/1")],
             github_token: Annotated[str, typer.Option(help="GitHub access token, for example, "
                                                            "github_pat_xxx_yyyyyy",
                                                       envvar=[constants.ENV_GITHUB_TOKEN])],
             model_name: Annotated[str, typer.Option(
                 help="The name of the AI model, such as gemini/gemini-1.5-flash")] = None,
             api_url: Annotated[str, typer.Option(
                 help="The request URL of the AI model API. If you use the official API, it is not required.")] = None,
             api_key: Annotated[str, typer.Option(
                 help="The API key of the model, for example, xxxyyyzzz")] = None,
             proxy_url: Annotated[str, typer.Option(
                 help="The url of the http proxy used when requesting the model's API, "
                      "for example, http://127.0.0.1:8118")] = None
             ):
    """
    Translate issues to english
    :return:
    """
    setup_result = settings.setup_translation_env(github_token, model_name, api_url, api_key, proxy_url)
    if not setup_result:
        return
    asyncio.run(trans.trans_pr(input_url))


@app.command("batch_trans", help="Batch translation repository for English")
def batch_trans(input_url: Annotated[
    str, typer.Option(help="GitHub repository URL, for example, https://github.com/your-org/your-repository")],
                github_token: Annotated[str, typer.Option(help="GitHub access token, for example, "
                                                               "github_pat_xxx_yyyyyy",
                                                          envvar=[constants.ENV_GITHUB_TOKEN])],
                query_filter: Annotated[
                    str, typer.Option(
                        help="The filter can be [issue, pr, pullrequest, discussion], for example, issue")],
                query_limit: Annotated[int, typer.Option(help="Maximum quantity at a time, for example 10")] = 10,
                model_name: Annotated[str, typer.Option(
                    help="The name of the AI model, such as gemini/gemini-1.5-flash")] = None,
                api_url: Annotated[str, typer.Option(
                    help="The request URL of the AI model API. If you use the official API, it is not required.")] = None,
                api_key: Annotated[str, typer.Option(
                    help="The API key of the model, for example, xxxyyyzzz")] = None,
                proxy_url: Annotated[str, typer.Option(
                    help="The url of the http proxy used when requesting the model's API, "
                         "for example, http://127.0.0.1:8118")] = None
                ):
    """
    Translate issues to english
    :return:
    """
    setup_result = settings.setup_translation_env(github_token, model_name, api_url, api_key, proxy_url)
    if not setup_result:
        return
    asyncio.run(trans.batch_trans(input_url, query_filter, query_limit))


@app.command("review_commit", help="Review a specific commit")
def review_specific_commit(input_url: Annotated[str, typer.Option(
    help="GitHub commit URL, for example, "
         "https://github.com/your-org/your-repository/commit/8768ec2f6bacc204f167ef19f15fb869664d9410")],
                           github_token: Annotated[str, typer.Option(help="GitHub access token, for example, "
                                                                          "github_pat_xxx_yyyyyy",
                                                                     envvar=[constants.ENV_GITHUB_TOKEN])],
                           model_name: Annotated[str, typer.Option(
                               help="The name of the AI model, such as gemini/gemini-1.5-flash")] = None,
                           api_url: Annotated[str, typer.Option(
                               help="The request URL of the AI model API. If you use the official API, it is not required.")] = None,
                           api_key: Annotated[str, typer.Option(
                               help="The API key of the model, for example, xxxyyyzzz")] = None,
                           proxy_url: Annotated[str, typer.Option(
                               help="The url of the http proxy used when requesting the model's API, "
                                    "for example, http://127.0.0.1:8118")] = None
                           ):
    """
    Translate issues to english
    :return:
    """
    setup_result = settings.setup_review_env(github_token, model_name, api_url, api_key, proxy_url)
    if not setup_result:
        return
    asyncio.run(review.review_specific_commit(input_url))


@app.command("review_pr", help="Review a specific pr")
def review_specific_pr(input_url: Annotated[str, typer.Option(
    help="GitHub commit URL, for example, "
         "https://github.com/ZLMediaKit/ZLMediaKit/pull/3758")],
                       github_token: Annotated[str, typer.Option(help="GitHub access token, for example, "
                                                                      "github_pat_xxx_yyyyyy",
                                                                 envvar=[constants.ENV_GITHUB_TOKEN])],
                       model_name: Annotated[str, typer.Option(
                           help="The name of the AI model, such as gemini/gemini-1.5-flash")] = None,
                       api_url: Annotated[str, typer.Option(
                           help="The request URL of the AI model API. If you use the official API, it is not required.")] = None,
                       api_key: Annotated[str, typer.Option(
                           help="The API key of the model, for example, xxxyyyzzz")] = None,
                       proxy_url: Annotated[str, typer.Option(
                           help="The url of the http proxy used when requesting the model's API, "
                                "for example, http://127.0.0.1:8118")] = None
                       ):
    """
    Translate issues to english
    :return:
    """
    setup_result = settings.setup_review_env(github_token, model_name, api_url, api_key, proxy_url)
    if not setup_result:
        return
    asyncio.run(review.review_specific_pr(input_url))


@app.command("webhook", help="The GitHub webhook server")
def start_bot_webhook(command: Annotated[str, typer.Argument(help="start/stop/restart")]):
    """
    Manage the webhook service
    :return:
    """
    from services import webhook
    if command == "start":
        webhook.webhook_service.start()
    elif command == "stop":
        webhook.webhook_service.stop()
    elif command == "restart":
        webhook.webhook_service.restart()
    else:
        console.print("Invalid command", style="bold red")


if __name__ == "__main__":
    system.check_env()
    install_panel()
    app()
