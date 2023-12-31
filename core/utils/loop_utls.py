# -*- coding:utf-8 -*-
__author__ = 'alex'


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
