# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/translation_issues).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
__author__ = 'alex'

import asyncio
import time
from asyncio import Queue


def use_uvloop():
    """
    uvloop
    :return:
    """
    try:
        import asyncio
        import uvloop

        if not isinstance(asyncio.get_event_loop_policy(), uvloop.EventLoopPolicy):
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            loop = uvloop.new_event_loop()
            asyncio.set_event_loop(loop)
    except ImportError:
        pass


class RateLimiter:
    def __init__(self, rate_limit, time_unit=60):
        self.rate_limit = rate_limit
        self.time_unit = time_unit
        self.token_bucket = Queue()
        self.last_check = time.monotonic()

    async def add_token(self):
        now = time.monotonic()
        time_passed = now - self.last_check
        self.last_check = now

        tokens_to_add = time_passed * (self.rate_limit / self.time_unit)
        for _ in range(int(tokens_to_add)):
            await self.token_bucket.put(1)

        if self.token_bucket.qsize() > self.rate_limit:
            self.token_bucket = Queue()
            for _ in range(self.rate_limit):
                await self.token_bucket.put(1)

    async def acquire(self):
        while self.token_bucket.empty():
            await self.add_token()
            if self.token_bucket.empty():
                await asyncio.sleep(1 / (self.rate_limit / self.time_unit))
        await self.token_bucket.get()
