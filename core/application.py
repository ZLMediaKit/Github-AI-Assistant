# -*- coding:utf-8 -*-
import atexit
import logging
import os
import signal
import time
from signal import SIG_IGN

from core import settings
from core.log import init_logging, logger

DEFAULT_PID_FILE_PATH = "/tmp/hkdvb/run"


class BaseApplication(object):
    """
    BaseApplication
    """
    def __init__(self, app_name: str, pid_file_path=None, log_file_path=None, config=None):
        """
        init
        :param config:
        """
        file_name = app_name.lower().strip().replace(" ", "_")
        self.app_name = app_name
        self.log_file_path = log_file_path
        self.sanic_app = None
        if pid_file_path:
            self.pid_file_path = pid_file_path
        else:
            self.pid_file_path = os.path.join(DEFAULT_PID_FILE_PATH, f"{file_name}.pid")
        init_logging(file_name, logger_path=log_file_path, logger_level=settings.LOGGER_LEVEL)
        self.config = config

        if os.getppid() == 1:
            atexit.register(self.delete_pid_file)

    def init(self):
        """
        init
        :return:
        """
        raise NotImplementedError

    def _setup_system_signals(self):
        """
        _setup_system_signals
        :return:
        """
        # 忽略SIGHUP信号
        signal.signal(signal.SIGHUP, SIG_IGN)

    def create_pid_file(self):
        """
        create_pid_file
        :return:
        """
        pid = str(os.getpid())
        # 判断文件夹是否存在, 如果不存在, 则创建
        if not os.path.exists(os.path.dirname(self.pid_file_path)):
            os.makedirs(os.path.dirname(self.pid_file_path))
        with open(self.pid_file_path, "w") as f:
            f.write(pid)

    def delete_pid_file(self):
        """
        delete_pid_file
        :return:
        """
        # 日志记录是因为什么原因退出程序
        logger.info(f"{self.app_name} shutdown")
        if os.path.exists(self.pid_file_path):
            os.remove(self.pid_file_path)

    def check_pid_status(self):
        """
        check_pid_status
        :return:
        """
        if os.path.exists(self.pid_file_path):
            # 判断这个pid是否存在
            with open(self.pid_file_path, "r") as f:
                pid = f.read()
            if os.path.exists("/proc/%s" % pid):
                logger.error(f"{self.app_name} already started")
                exit(1)
            else:
                logger.info(f"{self.app_name} starting")
                # 记录pid
                self.create_pid_file()
        else:
            logger.info(f"{self.app_name} starting")
            # 记录pid
            self.create_pid_file()

    def start(self, *args, **kwargs):
        """
        start
        :return:
        """
        self.check_pid_status()
        self.run(*args, **kwargs)

    def stop(self, *args, **kwargs):
        """
        stop服务器
        找到pid文件, 读取pid, 然后发送SIGTERM信号
        :return:
        """
        pid = 0
        if os.path.exists(self.pid_file_path):
            with open(self.pid_file_path, "r") as f:
                pid = f.read()
            if os.path.exists("/proc/%s" % pid):
                pid = int(pid)
                os.kill(pid, 15)
                logger.info(f"{self.app_name} stop success")
            else:
                logger.error(f"{self.app_name} not running")
        else:
            logger.error(f"{self.app_name} not running")
        return pid

    def restart(self, *args, **kwargs):
        """
        restart
        :return:
        """
        pid = self.stop(*args, **kwargs)
        if pid <= 0:
            time.sleep(5)
        else:
            while True:
                if os.path.exists("/proc/%s" % pid):
                    time.sleep(1)
                else:
                    break
        self.start(*args, **kwargs)

    def run(self, *args, **kwargs):
        """
        run
        :return:
        """
        raise NotImplementedError

    def shutdown(self, *args, **kwargs):
        """
        shutdown
        :param args:
        :param kwargs:
        :return:
        """
        print(args, kwargs)
        exit(0)

