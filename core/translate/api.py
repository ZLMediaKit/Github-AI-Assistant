# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/translation_issues).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
import httpx
import openai

from core import settings


async def do_gemini_translate(prompt: str, messages):
    """
    调用gemini翻译
    :param prompt:
    :param messages:
    :return:
    """
    gemini_key = settings.get_gemini_api_key()
    gemini_model = settings.get_gemini_model()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={gemini_key}"
    data = {
        "contents": [
            {
                "parts": []
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "topK": 1,
            "topP": 1,
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
    data["contents"][0]["parts"].insert(0, {"text": f"input: {prompt}"})
    for message in messages:
        data["contents"][0]["parts"].append({"text": f"input: {message['content']}"})

    headers = {
        "Content-Type": "application/json",
    }
    response = httpx.post(url, headers=headers, json=data, proxy=settings.get_proxy_url(), timeout=30)
    if response.status_code != 200:
        raise Exception(f"gemini request failed, code={response.status_code}")
    result_json = response.json()
    translated = result_json["candidates"][0]['content']["parts"][0]["text"]
    lines = translated.split('\n')
    if len(lines) > 0 and 'maintain' in lines[-1] and 'markdown structure' in lines[-1]:
        translated = '\n'.join(lines[:-1])
    return translated


async def do_openai_translate(prompt: str, messages):
    """
    调用openai翻译
    :param prompt:
    :param messages:
    :return:
    """
    prompts = messages.copy()
    if prompt is not None:
        prompts.insert(0, {"role": "system", "content": prompt})
    completion = openai.ChatCompletion.create(
        model=settings.get_gpt_model(),
        messages=prompts,
        temperature=0,
    )
    translated = completion.choices[0].message.content.strip('\'"')
    lines = translated.split('\n')
    if len(lines) > 0 and 'maintain' in lines[-1] and 'markdown structure' in lines[-1]:
        translated = '\n'.join(lines[:-1])
    return translated
