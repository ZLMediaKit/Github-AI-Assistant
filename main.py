# -*- coding:utf-8 -*-
import asyncio
import os.path
import signal
import sys
from threading import Event

import typer
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn, SpinnerColumn,
)
from rich.prompt import Prompt, Confirm, IntPrompt
from typing_extensions import Annotated

from apps import trans
from core import settings, constants, translate
from core.console import console
from core.log import init_logging, logger
from core.utils import system, env, systemd

app = typer.Typer(no_args_is_help=True,
                  help="Auto trans issues/pull requests/discussions to english")

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
init_logging("main", logger_path=None, logger_level=settings.LOGGER_LEVEL)


def get_spinner_progress(transient=False):
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=transient,
    )


def get_download_progress():
    return Progress(
        TextColumn("[bold blue]{task.fields[filename]}", justify="right"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        "•",
        TimeRemainingColumn(),
    )


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


def update_env_file():
    """
    update .env file
    :return:
    """
    enable_debug = Confirm.ask("Enable debug mode?",
                               console=console,
                               default=env.get_env(constants.ENV_DEBUG))
    env.update_env(constants.ENV_DEBUG, enable_debug)

    github_token_ask = Prompt.ask("Please input your github token",
                                  console=console,
                                  default=env.get_env(constants.ENV_GITHUB_TOKEN))
    env.update_env(constants.ENV_GITHUB_TOKEN, github_token_ask)
    openai_key_ask = Prompt.ask("Please input your openai key, leave none if not use openai",
                                console=console,
                                default=env.get_env(constants.ENV_OPENAI_KEY))
    env.update_env(constants.ENV_OPENAI_KEY, openai_key_ask)
    openai_endpoint_ask = Prompt.ask("Please enter your openAI (or similar openAI interface) API url. If you use the "
                                     "official API, you can leave it blank.",
                                     console=console,
                                     default=env.get_env(constants.ENV_OPENAI_URL))
    env.update_env(constants.ENV_OPENAI_URL, openai_endpoint_ask)
    gemini_key_ask = Prompt.ask("Please input your gemini key, leave none if not use openai",
                                console=console,
                                default=env.get_env(constants.ENV_GEMINI_KEY))
    env.update_env(constants.ENV_GEMINI_KEY, gemini_key_ask)
    if env.get_env(constants.ENV_OPENAI_KEY):
        gpt_model_ask = Prompt.ask("Please input your gpt model",
                                   console=console,
                                   default=env.get_env(constants.ENV_GPT_MODEL, "gpt-4-1106-preview"))
        env.update_env(constants.ENV_GPT_MODEL, gpt_model_ask)
    else:
        gemini_model_ask = Prompt.ask("Please input your gemini model",
                                      console=console,
                                      default=env.get_env(constants.ENV_GEMINI_MODEL, "gemini-1.5-flash"))
        env.update_env(constants.ENV_GEMINI_MODEL, gemini_model_ask)
    api_request_limit_ask = IntPrompt.ask("Please input your api request limit",
                                          console=console,
                                          default=env.get_env(constants.ENV_API_REQUEST_LIMIT, 10))
    env.update_env(constants.ENV_API_REQUEST_LIMIT, api_request_limit_ask)
    secret_key_ask = Prompt.ask("Please input your github webhook secret key",
                                console=console,
                                default=env.get_env(constants.ENV_SECRET_KEY))
    env.update_env(constants.ENV_SECRET_KEY, secret_key_ask)
    proxy_url_ask = Prompt.ask("Please input your proxy url, leave none if no proxy",
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
    console.print("Update .env file success", style="bold green")


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
    update_env_file()
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
    update_env_file()


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
                 openai_key: Annotated[str, typer.Option(
                     help="OpenAI API key, for example, xxxyyyzzz")] = None,
                 openai_url: Annotated[str, typer.Option(
                     help=" OpenAI (or similar openAI interface) API Url, for example, "
                          "http://127.0.0.1:8118/v1/")] = None,
                 gemini_key: Annotated[str, typer.Option(
                     help="Gemini API key, for example, xxxyyyzzz")] = None,
                 proxy_url: Annotated[str, typer.Option(
                     help="Proxy URL, used for openai or gemini api, for example, http://127.0.0.1:8118")] = None
                 ):
    """
    Translate issues to english
    :return:
    """
    setup_result = settings.setup_env(github_token, openai_key, openai_url, gemini_key, proxy_url)
    if not setup_result:
        return
    asyncio.run(trans.trans_issues(input_url))


@app.command("test", help="Test translate")
def test_translate(github_token: Annotated[str, typer.Option(help="GitHub access token, for example, "
                                                                  "github_pat_xxx_yyyyyy",
                                                             envvar=[constants.ENV_GITHUB_TOKEN])],
                   openai_key: Annotated[str, typer.Option(
                       help="OpenAI API key, for example, xxxyyyzzz")] = None,
                   openai_url: Annotated[str, typer.Option(
                       help=" OpenAI (or similar openAI interface) API Url, for example, "
                            "http://127.0.0.1:8118/v1/")] = None,
                   gemini_key: Annotated[str, typer.Option(
                       help="Gemini API key, for example, xxxyyyzzz")] = None,
                   proxy_url: Annotated[str, typer.Option(
                       help="Proxy URL, used for openai or gemini api, for example, http://127.0.0.1:8118")] = None
                   ):
    setup_result = settings.setup_env(github_token, openai_key, openai_url, gemini_key, proxy_url)
    if not setup_result:
        return
    console.print("Test translate, the original content is:", style="bold green")
    with open(os.path.join(BASE_PATH, "./test/test_issues.md"), "r") as f:
        md = f.read()
        console.print(md)
        translator = translate.get_translator(settings.get_translator(), max_tokens=settings.get_max_tokens())
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
                 openai_key: Annotated[str, typer.Option(
                     help="OpenAI API key, for example, xxxyyyzzz")] = None,
                 openai_url: Annotated[str, typer.Option(
                     help=" OpenAI (or similar openAI interface) API Url, for example, "
                          "http://127.0.0.1:8118/v1/")] = None,
                 gemini_key: Annotated[str, typer.Option(
                     help="Gemini API key, for example, xxxyyyzzz")] = None,
                 proxy_url: Annotated[str, typer.Option(
                     help="Proxy URL, used for openai or gemini api, for example, http://127.0.0.1:8118")] = None
                 ):
    """
    Translate issues to english
    :return:
    """
    setup_result = settings.setup_env(github_token, openai_key, openai_url, gemini_key, proxy_url)
    if not setup_result:
        return
    trans.trans_issues(input_url)


@app.command("trans_discussions", help="Translate a specific discussion into english")
def trans_discussion(input_url: Annotated[str, typer.Option(help="GitHub discussion URL, for example, "
                                                                 "https://github.com/your-org/your-repository/discussions/1")],
                     github_token: Annotated[str, typer.Option(help="GitHub access token, for example, "
                                                                    "github_pat_xxx_yyyyyy",
                                                               envvar=[constants.ENV_GITHUB_TOKEN])],
                     openai_key: Annotated[str, typer.Option(
                         help="OpenAI API key, for example, xxxyyyzzz")] = None,
                     openai_url: Annotated[str, typer.Option(
                         help=" OpenAI (or similar openAI interface) API Url, for example, "
                              "http://127.0.0.1:8118/v1/")] = None,
                     gemini_key: Annotated[str, typer.Option(
                         help="Gemini API key, for example, xxxyyyzzz")] = None,
                     proxy_url: Annotated[str, typer.Option(
                         help="Proxy URL, used for openai or gemini api, for example, http://127.0.0.1:8118")] = None
                     ):
    """
    Translate issues to english
    :return:
    """
    setup_result = settings.setup_env(github_token, openai_key, openai_url, gemini_key, proxy_url)
    if not setup_result:
        return
    trans.trans_discussion(input_url)


@app.command("trans_pr", help="Translate a specific PR into english")
def trans_pr(input_url: Annotated[str, typer.Option(help="GitHub PR URL, for example, "
                                                         "https://github.com/your-org/your-repository/pull/1")],
             github_token: Annotated[str, typer.Option(help="GitHub access token, for example, "
                                                            "github_pat_xxx_yyyyyy",
                                                       envvar=[constants.ENV_GITHUB_TOKEN])],
             openai_key: Annotated[str, typer.Option(
                 help="OpenAI API key, for example, xxxyyyzzz")] = None,
             openai_url: Annotated[str, typer.Option(
                 help=" OpenAI (or similar openAI interface) API Url, for example, "
                      "http://127.0.0.1:8118/v1/")] = None,
             gemini_key: Annotated[str, typer.Option(
                 help="Gemini API key, for example, xxxyyyzzz")] = None,
             proxy_url: Annotated[str, typer.Option(
                 help="Proxy URL, used for openai or gemini api, for example, http://127.0.0.1:8118")] = None
             ):
    """
    Translate issues to english
    :return:
    """
    setup_result = settings.setup_env(github_token, openai_key, openai_url, gemini_key, proxy_url)
    if not setup_result:
        return
    trans.trans_pr(input_url)


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
                openai_key: Annotated[str, typer.Option(
                    help="OpenAI API key, for example, xxxyyyzzz")] = None,
                openai_url: Annotated[str, typer.Option(
                    help=" OpenAI (or similar openAI interface) API Url, for example, "
                         "http://127.0.0.1:8118/v1/")] = None,
                gemini_key: Annotated[str, typer.Option(
                    help="Gemini API key, for example, xxxyyyzzz")] = None,
                proxy_url: Annotated[str, typer.Option(
                    help="Proxy URL, used for openai or gemini api, for example, http://127.0.0.1:8118")] = None
                ):
    """
    Translate issues to english
    :return:
    """
    setup_result = settings.setup_env(github_token, openai_key, openai_url, gemini_key, proxy_url)
    if not setup_result:
        return
    trans.batch_trans(input_url, query_filter, query_limit)


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
