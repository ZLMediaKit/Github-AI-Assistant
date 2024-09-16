# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
#
import logging

import httpx
import tenacity
from openai import AsyncClient

from core import settings
from core.log import logger
from core.models import ModelSettings




@tenacity.retry(
    retry=tenacity.retry_if_exception_type(Exception),
    wait=tenacity.wait_exponential(multiplier=1, min=2, max=5),
    stop=tenacity.stop_after_attempt(3),
    before_sleep=tenacity.before_sleep_log(logger, logging.INFO)
)
async def call_gemini_api(prompt: str, messages, model: ModelSettings, temperature: float = 0, top_k: float = 1,
                          top_p: float = 1):
    """
    call google gemini api
    :param top_p:
    :param top_k:
    :param temperature:
    :param model:
    :param prompt:
    :param messages:
    :return:
    """
    gemini_key = model.api_key
    gemini_model = model.model_name
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_key}"
    data = {
        "system_instruction": {
            "parts": {"text": prompt}
        },
        "contents": [
            {
                "parts": []
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "topK": top_k,
            "topP": top_p,
            "maxOutputTokens": 8192,
            "stopSequences": []
        },
        "safetySettings": [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_ONLY_HIGH"
            }
        ]
    }
    # data["contents"][0]["parts"].insert(0, {"text": f"input: {prompt}"})
    for message in messages:
        data["contents"][0]["parts"].append({"text": f"input: {message['content']}"})

    headers = {
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(proxy=settings.get_proxy_url()) as client:
        response = await client.post(url, headers=headers, json=data, timeout=30)
        if response.status_code != 200:
            raise Exception(f"gemini request failed, code={response.status_code}, text={response.text}")
        result_json = response.json()
        root = result_json["candidates"][0]
        if "content" not in root and root["finishReason"] == "SAFETY":
            logger.error("gemini response: %s", root)
            return ""
        translated = root['content']["parts"][0]["text"]
        lines = translated.split('\n')
        if len(lines) > 0 and 'maintain' in lines[-1] and 'markdown structure' in lines[-1]:
            translated = '\n'.join(lines[:-1])
        return translated


async def call_openai_api(prompt: str, messages, model: ModelSettings, api_base_url=None, temperature: float = 0,
                          top_k: float = 1, top_p: float = 1):
    """
    call openai api
    :param top_p:
    :param top_k:
    :param temperature:
    :param api_base_url:
    :param model:
    :param prompt:
    :param messages:
    :return:
    """
    prompts = messages.copy()
    if prompt is not None:
        prompts.insert(0, {"role": "system", "content": prompt})
    if not api_base_url:
        api_base_url = model.api_url
    client = AsyncClient(
        api_key=model.api_key,
        base_url=api_base_url,
        http_client=httpx.AsyncClient(timeout=30, proxy=settings.get_proxy_url())
    )
    completion = await client.chat.completions.create(model=model.model_name, messages=prompts,
                                                      temperature=temperature, top_p=top_p)
    translated = completion.choices[0].message.content.strip('\'"')
    lines = translated.split('\n')
    if len(lines) > 0 and 'maintain' in lines[-1] and 'markdown structure' in lines[-1]:
        translated = '\n'.join(lines[:-1])
    return translated


async def call_ai_api(prompt: str, messages, model: ModelSettings, temperature: float = 0,
                      top_k: float = 1, top_p: float = 1):
    """
    call ai api
    :param prompt:
    :param messages:
    :param model:
    :param temperature:
    :param top_k:
    :param top_p:
    :return:
    """
    await settings.get_api_limiter(model.api_key).acquire()
    if model.provider == 'openai':
        return await call_openai_api(prompt, messages, model, temperature, top_k, top_p)
    elif model.provider == 'gemini':
        return await call_gemini_api(prompt, messages, model)
    elif model.provider == 'groq':
        return await call_openai_api(prompt, messages, model, "https://api.groq.com/openai/v1", 0.1)
    elif model.provider == 'openai_like':
        return await call_openai_api(prompt, messages, model, None, 0.1)
    else:
        raise Exception(f"unknown provider {model.provider}")


async def do_ai_translate(system_prompt: str, messages):
    translated = await call_ai_api(system_prompt, messages, settings.TRANSLATION_MODEL)
    return translated



