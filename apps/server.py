# -*- coding:utf-8 -*-
__author__ = 'alex'

import asyncio
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor

from sanic import Sanic, response, text
from sanic.log import logger as sanic_logger
from sanic.response import empty

from apps import trans
from core.utils import loop_utls
from core import settings, github_helper
from core.log import LOGGING_CONFIG_DEFAULTS, logger

loop_utls.use_uvloop()

app = Sanic("Webhook", strict_slashes=True, log_config=LOGGING_CONFIG_DEFAULTS)
app.ctx.threads = ThreadPoolExecutor()


@app.before_server_start
async def before_start(app_instance, loop):
    if settings.DEBUG:
        sanic_logger.setLevel(logging.DEBUG)
    else:
        sanic_logger.setLevel(logging.INFO)


@app.before_server_stop
async def before_stop(app_instance: Sanic, loop):
    pass





@app.post("/api/v1/hooks")
async def github_hook(request):
    secret_key = settings.get_secret_key()
    if secret_key:
        try:
            github_helper.verify_signature(request.body, secret_key, request.headers.get("X-Hub-Signature-256"))
        except Exception as e:
            logger.error(f"verify_signature failed: {e}")
            return response.json({"message": "invalid secret_key"}, status=403)
    request_event = request.headers.get("X-GitHub-Event")
    request_delivery = request.headers.get("X-GitHub-Delivery")
    if not request_event or not request_delivery:
        return response.json({"message": "invalid request"}, status=400)
    data = request.json
    logger.info(f"Received event: {request_event}, delivery: {request_delivery}")
    hook = None
    if 'hook' in data and 'config' in data['hook'] and 'url' in data['hook']['config']:
        hook = data['hook']['config']['url']
    logger.info(f"{request_delivery}: Get event={request_event}, hook={hook}, headers={request.headers}")

    if request_event in github_helper.ALLOWED_EVENTS:
        logger.info(f"{request_delivery}: handle {request_event}")
        app.ctx.threads.submit(trans.handle_github_request, data, request_event, request_delivery, request.headers)
    else:
        print(f"{request_delivery}: Ignore event {request_event}")
    return empty(status=200)
