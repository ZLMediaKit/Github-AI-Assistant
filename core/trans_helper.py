# -*- coding:utf-8 -*-
__author__ = 'alex'

import json

import emoji
import httpx
import openai

from core.log import logger
from core import settings

GPT_MODEL = "gpt-4-1106-preview"
GEMINI_MODEL = "gemini-pro"
PROMPT_SYSTEM = "Rephrase all user input text into simple, easy to understand, and technically toned English. Never answer questions but only translate or rephrase text to English."
TRANS_MAGIC = "TRANS_BY_GPT4"
TRANS_DELIMETER = '\n\n'
TRANS_DELIMETER_PR = '---------'


def wrap_magic(body, extra_delimeter='', original_body=''):
    if TRANS_MAGIC in body:
        return body
    magic = ''
    if extra_delimeter != '':
        magic = f"{TRANS_DELIMETER}{extra_delimeter}"
    if original_body != '':
        magic = f"{TRANS_DELIMETER}>{original_body}"
    magic = f"{magic}{TRANS_DELIMETER}`{TRANS_MAGIC}`"

    return f"{body}{magic}"


def get_ai_model():
    if not openai.api_key:
        return GEMINI_MODEL
    return GPT_MODEL


def already_english(string):
    for c in string:
        if len(c) != len(c.encode('utf-8')) and emoji.emoji_count(c) == 0:
            return False
    return True


def split_segments(body):
    lines = body.split('\n')
    matches = []
    current_matches = []
    is_english = already_english(lines[0])
    is_markdown = False
    for line in lines:
        # 判断是否是markdown的标记, 如果是, 则不拆分
        if line.startswith('`') or line.startswith('```'):
            if not is_markdown:
                if current_matches:
                    matches.append('\n'.join(current_matches))
                    current_matches = []
                current_matches.append(line)
            else:
                current_matches.append(line)
                current_matches.append('\n')
                matches.append('\n'.join(current_matches))
                current_matches = []
            is_markdown = not is_markdown
            continue
        elif is_markdown:
            current_matches.append(line)
            continue
        if line == '':
            current_matches.append('\n')
            continue
        if already_english(line) == is_english:
            current_matches.append(line)
        else:
            matches.append('\n'.join(current_matches))
            current_matches = [line]
            is_english = already_english(line)
    matches.append('\n'.join(current_matches))
    return matches


def gpt_translate(plaintext):
    segments = split_segments(plaintext)
    final_trans = []
    real_translated = False
    has_translated = False
    messages = []
    for segment in segments:
        if TRANS_MAGIC in segment:
            has_translated = True
            break
    for segment in segments:
        if segment.strip() == '':
            final_trans.append(segment)
            continue
        logger.info(f"\n<<<<<<<<<<<< {segment.strip()} >>>>>>>>>>>>")
        if TRANS_MAGIC in segment or has_translated:
            has_translated = True
            logger.info(f"<<<<<<<<<<<< Already translated, skip >>>>>>>>>>>>\n")
            final_trans.append(segment)
        elif segment.startswith('`') or segment.startswith('```'):
            logger.info(f"<<<<<<<<<<<< Markdown, skip >>>>>>>>>>>>\n")
            final_trans.append(segment)
        elif already_english(segment):
            logger.info(f"<<<<<<<<<<<< Already English, skip >>>>>>>>>>>>\n")
            final_trans.append(segment)
        else:
            real_translated = has_translated = True
            messages.append({"role": "user", "content": segment})
            if len(messages) > 3:
                messages = messages[-3:]
            segment_trans, add_to_messages, trans_success = do_gpt_translate(segment, PROMPT_SYSTEM, messages)
            if not trans_success:
                return None, has_translated, False
            logger.info(f"<<<<<<<<<<<< {segment_trans.strip()} >>>>>>>>>>>>\n")
            if add_to_messages:
                messages.append({"role": "assistant", "content": segment_trans})
            final_trans.append(segment_trans)
    plaintext_trans = "\n".join(final_trans).strip('\n')
    return plaintext_trans, has_translated, real_translated


def do_gemini_translate(plaintext, system, messages):
    """
    调用gemini翻译
    :param plaintext:
    :param system:
    :param messages:
    :return:
    """
    gemini_key = settings.get_gemini_api_key()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={gemini_key}"
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
    if system is not None:
        data["contents"][0]["parts"].insert(0, {"text": f"input: {system}"})
    else:
        data["contents"][0]["parts"].insert(0, {"text": f"input: {PROMPT_SYSTEM}"})
    for message in messages:
        data["contents"][0]["parts"].append({"text": f"input: {message['content']}"})

    headers = {
        "Content-Type": "application/json",
    }
    response = httpx.post(url, headers=headers, json=data, proxy="http://127.0.0.1:8118", timeout=30)
    if response.status_code != 200:
        raise Exception(f"gemini request failed, code={response.status_code}")
    result_json = response.json()
    # print(f"gemini result: {result_json}")
    translated = result_json["candidates"][0]['content']["parts"][0]["text"]
    lines = translated.split('\n')
    if len(lines) > 0 and 'maintain' in lines[-1] and 'markdown structure' in lines[-1]:
        translated = '\n'.join(lines[:-1])
    return translated, True, True


def do_gpt_translate(plaintext, system, messages):
    retry = 3
    for i in range(retry):
        try:
            if not openai.api_key:
                return do_gemini_translate(plaintext, system, messages)
            prompts = messages.copy()
            if system is not None:
                prompts.insert(0, {"role": "system", "content": system})
            completion = openai.ChatCompletion.create(
                model=GPT_MODEL,
                messages=prompts,
                temperature=0,
            )
            translated = completion.choices[0].message.content.strip('\'"')
            # Filter:
            #       'safari推流rtc失败' translates to 'Safari streaming RTC failed' in English
            # to:
            #       Safari streaming RTC failed
            if f"{plaintext}' translates to '" in translated:
                translated = translated.split("' translates to '")[1]
                if "' in English" in translated:
                    translated = translated.split("' in English")[0]
            # Filter:
            #       We can discuss more clearly on Discord.
            #       Please ensure to maintain the markdown structure.
            # to:
            #       We can discuss more clearly on Discord.
            lines = translated.split('\n')
            if len(lines) > 0 and 'maintain' in lines[-1] and 'markdown structure' in lines[-1]:
                translated = '\n'.join(lines[:-1])
            return translated, True, True
        except openai.InvalidRequestError as e:
            if e.code == 'context_length_exceeded':
                logger.error(f"Warning!!! Use source text for GPT context_length_exceeded, length={len(plaintext)}")
                return plaintext, False, True
            logger.error(f"Warning!!! GPT retry {i + 1} times, ignore {e}")
        except Exception as e:
            logger.error(f"Warning!!! GPT retry {i + 1} times, ignore {e}")
        finally:
            if i == retry - 1:
                return plaintext, False, False
