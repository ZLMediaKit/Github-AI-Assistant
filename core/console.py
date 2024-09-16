# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
__author__ = 'alex'

from typing import Union, List, Dict, Any, Optional
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn, SpinnerColumn,
)
from rich.console import Console
from rich.panel import Panel

console = Console()



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


def select_prompt(prompt: str, options: Union[List[Any], Dict[str, Any]], max_retries: int = 99, default: Optional[Union[str, int]] = None,) -> Any:
    import tenacity
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(max_retries),
        retry=tenacity.retry_if_exception_type(ValueError),
        wait=tenacity.wait_fixed(1)
    )
    def _select() -> Any:
        if isinstance(options, list):
            options_dict = {str(i): v for i, v in enumerate(options, 1)}
        elif isinstance(options, dict):
            options_dict = {str(i): v for i, v in enumerate(options.keys(), 1)}
        else:
            raise ValueError("Options must be a list or a dictionary")

        # Find the default key
        default_key = None
        for k, v in options_dict.items():
            if v == default:
                default_key = k
                break

        # Create a panel with options
        options_text = ""
        for k, v in options_dict.items():
            line = f"[cyan]{k}[/cyan]: {v}"
            if v == default:
                line += " [yellow](default)[/yellow]"
            options_text += line + "\n"
        panel = Panel(options_text.strip(), title="Options", expand=False, border_style="bold")

        # Print the panel
        console.print(panel)

        # Get user input
        if default_key:
            choice = console.input(f"{prompt} [yellow](default: {default})[/yellow]: ")
        else:
            choice = console.input(f"{prompt}: ")

        if choice == "" and default_key:
            return options_dict[default_key]
        elif choice in options_dict:
            return options_dict[choice]
        else:
            raise ValueError(f"Invalid selection. Please choose from {', '.join(options_dict.keys())}")

    try:
        return _select()
    except tenacity.RetryError:
        console.print("[bold red]Max retries reached. Exiting.[/bold red]")
        return None
