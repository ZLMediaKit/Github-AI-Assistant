# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/translation_issues).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#

from sanic import Sanic, response, Request
from sanic.response import empty
from apps.webhook import handles
from core import settings
from core.log import logger
from core.utils import github

app_instance = Sanic.get_app()


@app_instance.post("/api/v1/hooks")
async def github_hook(request: Request):
    secret_key = settings.get_secret_key()
    if secret_key:
        try:
            github.verify_signature(request.body, secret_key, request.headers.get("X-Hub-Signature-256"))
        except Exception as e:
            logger.error(f"verify_signature failed: {e}")
            return response.json({"message": "invalid secret_key"}, status=403)
    request_event = request.headers.get("x-github-event")
    request_delivery = request.headers.get("x-github-delivery")
    logger.info(f"Received event: {request_event}, delivery: {request_delivery}")
    if not request_event or not request_delivery:
        logger.error(f"invalid request: {request.headers}")
        return response.json({"message": "invalid request"}, status=400)
    data = request.json
    hook = None
    if 'hook' in data and 'config' in data['hook'] and 'url' in data['hook']['config']:
        hook = data['hook']['config']['url']
    logger.info(f"{request_delivery}: Get event={request_event}, hook={hook}, headers={request.headers}")

    if request_event in github.ALLOWED_EVENTS:
        logger.info(f"{request_delivery}: handle {request_event}")
        _ = app_instance.add_task(handles.handle_github_request(data, request_event, request_delivery, request.headers))
    else:
        logger.info(f"{request_delivery}: Ignore event {request_event}")
    return empty(status=200)
