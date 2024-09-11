# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
import os
import re
from pathlib import Path

from core.console import console
from core.utils import system


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


def auto_start_when_boot(enable: bool = False, start_cmd: str = "./run.sh webhook start"):
    """
    Auto start when boot
    :return:
    """
    # 设置/etc/rc.local有执行权限
    system.run_cmd("chmod +x /etc/rc.local", True, True)
    with open("/etc/rc.local", "r") as f:
        content = f.read()
    # 使用正则表达式从content判断当前是否已经插入了启动命令
    if re.search(r"./run.sh", content):
        is_enable = True
        console.print("Current is auto start when boot", style="bold green")
    else:
        is_enable = False
        console.print("Current is not auto start when boot", style="bold green")
    if is_enable == enable:
        console.print("Current mode not changed", style="bold red")
        return
    project_path = Path(__file__).resolve().parent.parent
    if enable:
        content = content.replace("exit 0", f"cd {project_path}\n{start_cmd}\nexit 0")
    else:
        content = content.replace(f"cd {project_path}\n{start_cmd}\n", "")
    with open("/etc/rc.local", "w") as f:
        f.write(content)
    console.print("You have set auto start when boot is %s" % enable, style="bold green")
