# -*- coding:utf-8 -*-
import atexit
import os.path
import re
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

from apps import trans, server
from core import settings, constants
from core.console import console
from core.utils import system, env

app = typer.Typer(no_args_is_help=True,
                  help="Auto trans issues/pull requests/discussions to english")

BASE_PATH = os.path.dirname(os.path.abspath(__file__))


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
    if enable_debug != env.get_env(constants.ENV_DEBUG):
        env.set_env(constants.ENV_DEBUG, enable_debug, True)

    github_token_ask = Prompt.ask("Please input your github token",
                                  console=console,
                                  default=env.get_env(constants.ENV_GITHUB_TOKEN))
    if github_token_ask != env.get_env(constants.ENV_GITHUB_TOKEN):
        env.set_env(constants.ENV_GITHUB_TOKEN, github_token_ask, True)
    openai_key_ask = Prompt.ask("Please input your openai key",
                                console=console,
                                default=env.get_env(constants.ENV_OPENAI_KEY))
    if openai_key_ask != env.get_env(constants.ENV_OPENAI_KEY):
        env.set_env(constants.ENV_OPENAI_KEY, openai_key_ask, True)
    openai_proxy_ask = Prompt.ask("Please input your openai proxy",
                                  console=console,
                                  default=env.get_env(constants.ENV_OPENAI_PROXY))
    if openai_proxy_ask != env.get_env(constants.ENV_OPENAI_PROXY):
        env.set_env(constants.ENV_OPENAI_PROXY, openai_proxy_ask, True)
    gemini_key_ask = Prompt.ask("Please input your gemini key",
                                console=console,
                                default=env.get_env(constants.ENV_GEMINI_KEY))
    if gemini_key_ask != env.get_env(constants.ENV_GEMINI_KEY):
        env.set_env(constants.ENV_GEMINI_KEY, gemini_key_ask, True)
    secret_key_ask = Prompt.ask("Please input your github webhook secret key",
                                console=console,
                                default=env.get_env(constants.ENV_SECRET_KEY))
    if secret_key_ask != env.get_env(constants.ENV_SECRET_KEY):
        env.set_env(constants.ENV_SECRET_KEY, secret_key_ask, True)
    while True:
        server_port_ask = IntPrompt.ask("Please input your server listen port",
                                        console=console,
                                        default=env.get_env(constants.ENV_SERVER_PORT))
        if not (0 < server_port_ask < 65535):
            console.print("Server port must be a number and between 0 and 65535", style="bold red")
        else:
            if server_port_ask != env.get_env(constants.ENV_SERVER_PORT):
                env.set_env(constants.ENV_SERVER_PORT, server_port_ask, True)
            break
    console.print("Update .env file success", style="bold green")


def install_panel():
    """
    Install panel
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
    install_startup()
    system.run_cmd("chmod +x /etc/rc.local", True, True)
    with open("/etc/rc.local", "r") as f:
        content = f.read()
    if re.search(r"bash ./run.sh start_server", content):
        is_enable = True
        console.print("Current is auto start when boot", style="bold green")
    else:
        is_enable = False
        console.print("Current is not auto start when boot", style="bold green")
    if is_enable == enable:
        console.print("Current mode not changed", style="bold red")
        return
    if enable:
        content = content.replace("exit 0", f"cd {BASE_PATH}\nbash ./run.sh start_server\nexit 0")
    else:
        content = content.replace(f"cd {BASE_PATH}\nbash ./run.sh start_server\n", "")
    with open("/etc/rc.local", "w") as f:
        f.write(content)
    console.print("You have set auto start when boot is %s" % enable, style="bold green")


def install_startup():
    rc_content = open("./deploy/config/systemd/rc.local", "r").read()
    is_need_systemd_service = False
    if not os.path.exists("/etc/rc.local"):
        with open("/etc/rc.local", "w") as f:
            f.write("#!/bin/sh -e\n")
            f.write(rc_content)
            f.write("exit 0\n")
        os.chmod("/etc/rc.local", 0o755)
        is_need_systemd_service = True
    else:
        with open("/etc/rc.local", "r") as f:
            content = f.read()
        if rc_content not in content:
            with open("/etc/rc.local", "w") as f:
                f.write(content.replace("exit 0", rc_content + "\nexit 0"))
            os.chmod("/etc/rc.local", 0o755)
    if is_need_systemd_service:
        console.print("Installing startup", style="bold green")
        rc_local_service_content = open("./deploy/config/systemd/rc-local.service", "r").read()
        if not os.path.exists("/etc/systemd/system/rc-local.service"):
            with open("/etc/systemd/system/rc-local.service", "w") as f:
                f.write(rc_local_service_content)
            os.chmod("/etc/systemd/system/rc-local.service", 0o755)
            system.run_cmd("systemctl enable rc-local", True, True)
            system.run_cmd("systemctl daemon-reload", True, True)
            system.run_cmd("systemctl start rc-local", True, True)
        console.print("Install startup success", style="bold green")


@app.command("trans_issues", help="Translate a specific issue into english")
def trans_issues(input_url: Annotated[str, typer.Option(help="GitHub issue URL, for example, "
                                                             "https://github.com/your-org/your-repository/issues/1")],
                 github_token: Annotated[str, typer.Option(help="GitHub access token, for example, "
                                                                "github_pat_xxx_yyyyyy",
                                                           envvar=[constants.ENV_GITHUB_TOKEN])],
                 openai_key: Annotated[str, typer.Option(help="OpenAI API key, for example, xxxyyyzzz")] = None,
                 openai_proxy: Annotated[str, typer.Option(help="OpenAI API proxy, for example, x.y.z")] = None,
                 gemini_key: Annotated[str, typer.Option(help="Gemini API key, for example, xxxyyyzzz")] = None):
    """
    Translate issues to english
    :return:
    """
    setup_result = settings.setup_env(github_token, openai_key, openai_proxy, gemini_key)
    if not setup_result:
        return
    trans.trans_issues(input_url)


@app.command("trans_discussions", help="Translate a specific discussion into english")
def trans_discussion(input_url: Annotated[str, typer.Option(help="GitHub discussion URL, for example, "
                                                                 "https://github.com/your-org/your-repository/discussions/1")],
                     github_token: Annotated[str, typer.Option(help="GitHub access token, for example, "
                                                                    "github_pat_xxx_yyyyyy",
                                                               envvar=[constants.ENV_GITHUB_TOKEN])],
                     openai_key: Annotated[str, typer.Option(help="OpenAI API key, for example, xxxyyyzzz")] = None,
                     openai_proxy: Annotated[str, typer.Option(help="OpenAI API proxy, for example, x.y.z")] = None,
                     gemini_key: Annotated[str, typer.Option(help="Gemini API key, for example, xxxyyyzzz")] = None):
    """
    Translate issues to english
    :return:
    """
    setup_result = settings.setup_env(github_token, openai_key, openai_proxy, gemini_key)
    if not setup_result:
        return
    trans.trans_discussion(input_url)


@app.command("trans_pr", help="Translate a specific PR into english")
def trans_pr(input_url: Annotated[str, typer.Option(help="GitHub PR URL, for example, "
                                                         "https://github.com/your-org/your-repository/pull/1")],
             github_token: Annotated[str, typer.Option(help="GitHub access token, for example, "
                                                            "github_pat_xxx_yyyyyy",
                                                       envvar=[constants.ENV_GITHUB_TOKEN])],
             openai_key: Annotated[str, typer.Option(help="OpenAI API key, for example, xxxyyyzzz")] = None,
             openai_proxy: Annotated[str, typer.Option(help="OpenAI API proxy, for example, x.y.z")] = None,
             gemini_key: Annotated[str, typer.Option(help="Gemini API key, for example, xxxyyyzzz")] = None):
    """
    Translate issues to english
    :return:
    """
    setup_result = settings.setup_env(github_token, openai_key, openai_proxy, gemini_key)
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
                openai_key: Annotated[str, typer.Option(help="OpenAI API key, for example, xxxyyyzzz")] = None,
                openai_proxy: Annotated[str, typer.Option(help="OpenAI API proxy, for example, x.y.z")] = None,
                gemini_key: Annotated[str, typer.Option(help="Gemini API key, for example, xxxyyyzzz")] = None):
    """
    Translate issues to english
    :return:
    """
    setup_result = settings.setup_env(github_token, openai_key, openai_proxy, gemini_key)
    if not setup_result:
        return
    trans.batch_trans(input_url, query_filter, query_limit)


@app.command("start_server", help="Start the GitHub webhook server")
def start_server(listen_port: Annotated[int, typer.Option(help="Listen port, for example, 15372",
                                                          min=1, max=65535, clamp=True,
                                                          envvar=[constants.ENV_SERVER_PORT])],
                 github_token: Annotated[str, typer.Option(help="GitHub access token, for example, "
                                                                "github_pat_xxx_yyyyyy",
                                                           envvar=[constants.ENV_GITHUB_TOKEN])],
                 secret_key: Annotated[str, typer.Option(help="Secret key, for example, xxx_yyyyyy")] = None,
                 openai_key: Annotated[str, typer.Option(help="OpenAI API key, for example, xxxyyyzzz")] = None,
                 openai_proxy: Annotated[str, typer.Option(help="OpenAI API proxy, for example, x.y.z")] = None,
                 gemini_key: Annotated[str, typer.Option(help="Gemini API key, for example, xxxyyyzzz")] = None):
    """
    Translate issues to english
    :return:
    """
    setup_result = settings.setup_env(github_token, openai_key, openai_proxy, gemini_key, secret_key)
    if not setup_result:
        return
    atexit.register(system.delete_pid_file)
    if not system.check_pid_status():
        return
    console.print("Starting server", style="bold green")
    console.print(f"Your webhook is running at http://0.0.0.0:{listen_port}/api/v1/hooks", style="bold green")
    console.print(f"Your webhook secret key is {settings.get_secret_key()}", style="bold green")
    server.app.run(host="0.0.0.0", port=listen_port,
                   debug=settings.DEBUG,
                   auto_reload=settings.DEBUG,
                   workers=1,
                   access_log=not settings.DEBUG)


if __name__ == "__main__":
    system.check_env()
    install_panel()
    app()
