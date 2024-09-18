# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
"""
@author:alex
@date:2024/9/18
@time:上午1:43
"""
__author__ = 'alex'

import threading
from concurrent.futures import ThreadPoolExecutor
import atexit
import asyncio
from typing import Callable, Any
import os


class BackendThreadPool:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(BackendThreadPool, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.cpu_count = os.cpu_count() or 1
        self.executor = ThreadPoolExecutor(max_workers=self._get_default_workers())
        self._is_shutdown = False
        atexit.register(self.shutdown)

    def _get_default_workers(self):
        return max(self.cpu_count, 4)

    def get_executor(self):
        if self._is_shutdown:
            self._initialize()
        return self.executor

    def shutdown(self):
        if not self._is_shutdown:
            self.executor.shutdown()
            self._is_shutdown = True

    async def run_in_thread(self, func: Callable, *args, **kwargs) -> Any:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.get_executor(), lambda: func(*args, **kwargs))

    def set_max_workers(self, workers: int):
        """允许动态调整线程池大小"""
        if workers > 0:
            self.shutdown()
            self.executor = ThreadPoolExecutor(max_workers=workers)
            self._is_shutdown = False


# 全局访问点

def get_backend_thread_pool():
    return BackendThreadPool()
