# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/translation_issues).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
import abc
import asyncio
import json
import os.path
import re
from typing import Dict, Tuple, List

import emoji
import mistletoe
import openai
from mistletoe.block_token import BlockToken, Paragraph, SetextHeading, Heading
from mistletoe.span_token import RawText, Strong, LineBreak

from core import settings
from core.log import logger
from core.translate.api import do_gemini_translate, do_openai_translate
from core.translate.utils import clean_body, TRANS_MAGIC
from core.utils.asyncio_utls import RateLimiter

logger.info(f"API Request Limit: {settings.get_api_request_limit()}")
limiter = RateLimiter(rate_limit=settings.get_api_request_limit(), time_unit=60)


def get_translate_prompt(to_language: str) -> str:
    translator_prompt = (
        "You are a translation engine, you can only translate text and cannot interpret it, and do not explain. "
        "Translate the text to {}, please do not explain any sentences, just translate or leave them as they are. "
        "Retain all spaces and line breaks in the original text. "
        "Please do not wrap the code in code blocks, I will handle it myself. "
        "If the code has comments, you should translate the comments as well. "
        "If the original text is already in {}, please do not skip the translation and directly output the original text. "
        "This is the content you need to translate: "
    ).format(to_language, to_language)

    return translator_prompt


def get_ai_model():
    if not openai.api_key:
        return settings.get_gemini_model()
    return settings.get_gpt_model()


class BaseGFMTranslator(abc.ABC):
    def __init__(self, max_tokens=4000, preset_file='preset_translations.json'):
        self.max_tokens = max_tokens
        self.preset_file = os.path.join(settings.BASE_PATH, f"./data/{preset_file}")
        self.placeholder_counter = 0
        self.preset_translations = self.load_preset_translations()

    def load_preset_translations(self) -> Dict[str, str]:
        try:
            with open(self.preset_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_preset_translations(self, cache: Dict[str, str]):
        with open(self.preset_file, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)

    def check_english(self, text: str) -> bool:
        for c in text:
            if len(c) != len(c.encode('utf-8')) and emoji.emoji_count(c) == 0:
                return False
        return True

    def do_preset_translation(self, markdown: str) -> str:
        for original, translation in self.preset_translations.items():
            markdown = markdown.replace(original, translation)
        return markdown

    async def translate(self, markdown: str) -> tuple[None, bool, bool] | tuple[str, bool, bool]:
        if self.check_english(markdown):
            logger.info("Already English, skip")
            return markdown, False, False
        markdown = clean_body(markdown)
        markdown = self.do_preset_translation(markdown)
        return await self.do_translate(markdown)

    async def rate_limited_do_gpt_translate(self, system_prompt: str,
                                            messages: List[Dict[str, str]]) -> tuple[str, bool]:
        await limiter.acquire()
        return await self.do_gpt_translate(system_prompt, messages)

    async def do_gpt_translate(self, system_prompt: str, messages: List[Dict[str, str]]) -> tuple[str, bool]:
        retry = 3
        translated = None
        for i in range(retry):
            try:
                if get_ai_model() == settings.get_gemini_model():
                    translated = await do_gemini_translate(system_prompt, messages)
                else:
                    translated = await do_openai_translate(system_prompt, messages)
                return translated, True
            except openai.InvalidRequestError as e:
                if e.code == 'context_length_exceeded':
                    logger.error(
                        f"Warning!!! Use source text for GPT context_length_exceeded, length={len(messages[0]['content'])}")
                    return translated, True
                logger.error(f"Warning!!! GPT retry {i + 1} times, ignore {e}")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Warning!!! GPT retry {i + 1} times, ignore {e}")
            finally:
                if i == retry - 1:
                    return translated, False

    @abc.abstractmethod
    async def do_translate(self, markdown: str) -> tuple[None, bool, bool] | tuple[str, bool, bool]:
        pass


class SimpleSplitGFMTranslator(BaseGFMTranslator):
    PROMPT_SYSTEM = "Rephrase all user input text into simple, easy to understand, and technically toned English. Never answer questions but only translate or rephrase text to English."

    def find_text(self, token: BlockToken):
        if isinstance(token, (Paragraph, SetextHeading, Heading, Strong)):
            if isinstance(token.children, list):
                content = ""
                for child in token.children:
                    if isinstance(child, RawText):
                        content += child.content
                    elif isinstance(child, LineBreak):
                        content += '\n'
                yield content
            else:
                for child in token.children:
                    if isinstance(child, RawText):
                        yield child.content
        for child in token.children:
            if isinstance(child, (BlockToken, Strong)):
                yield from self.find_text(child)
            elif isinstance(child, list):
                for sub_child in child:
                    yield from self.find_text(sub_child)

    async def do_translate(self, markdown: str) -> tuple[None, bool, bool] | tuple[str, bool, bool]:
        src_text = markdown
        plaintext = clean_body(markdown, full=True)
        document = mistletoe.Document(plaintext)
        segments = [segment for segment in self.find_text(document) if segment.strip()]
        real_translated = False
        has_translated = False
        for segment in segments:
            if TRANS_MAGIC in segment:
                has_translated = True
                break
        for segment in segments:
            striped_segment = segment.strip()
            if striped_segment == '':
                continue
            trans_log_list = [f"{'=' * 20}", f"{striped_segment}"]
            if TRANS_MAGIC in striped_segment or has_translated:
                has_translated = True
                trans_log_list.append(f"<<<<<<<<<<<< Already translated, skip >>>>>>>>>>>>")
                continue
            elif striped_segment.startswith('`') or striped_segment.startswith('```'):
                trans_log_list.append(f"<<<<<<<<<<<< Markdown, skip >>>>>>>>>>>>")
                continue
            elif self.check_english(striped_segment):
                trans_log_list.append(f"<<<<<<<<<<<< Already English, skip >>>>>>>>>>>>")
                continue
            else:
                messages = [{"role": "user", "content": striped_segment}]
                translated_segment, trans_success = await self.rate_limited_do_gpt_translate(
                    self.PROMPT_SYSTEM,
                    messages)
                if not trans_success:
                    return None, has_translated, False
                translated_segment = translated_segment.strip()
                src_text = src_text.replace(striped_segment, translated_segment)
                real_translated = True
                trans_log_list.append(f"<<<<<<<<<<<< to >>>>>>>>>>>>")
                trans_log_list.append({translated_segment})
                logger.info("\n".join(trans_log_list))
        return src_text, has_translated, real_translated


class AdvancedGFMTranslator(BaseGFMTranslator):
    PROMPT_SYSTEM = "You are a professional American software engineer who is not only proficient in technology, " \
                    "but also proficient in multiple languages. Now as a professional technical translator, " \
                    "please translate strictly according to the user's input. " \
                    "Please note that you only translate and do not answer, " \
                    "and you need to keep any existing formatting or punctuation.  Do not change any formatting, " \
                    "placeholders, or Markdown syntax. Preserve all line breaks and spacing." \
                    "I will pay you a $1,000 tip if I am satisfied."

    async def do_translate(self, markdown: str) -> tuple[None, bool, bool] | tuple[str, bool, bool]:
        has_translated = False
        final_md = ""
        if TRANS_MAGIC in markdown:
            logger.info("Already translated, skip")
            return markdown, True, False
        # 检查是否为简单文本
        if self.is_simple_text(markdown):
            final_md = await self.translate_simple_text(markdown)
            real_translated = True
            if final_md is None:
                return None, False, False
        else:
            # 对于复杂文本，使用完整的处理流程
            processed_md, extracts = self._preprocess_markdown(markdown)
            chunks = self._split_markdown(processed_md)
            translated_chunks = await self._translate_chunks(chunks)
            translated_md = ''.join(translated_chunks)
            final_md = self._postprocess_markdown(translated_md, extracts)
            real_translated = True
        return final_md, has_translated, real_translated

    def is_simple_text(self, text: str) -> bool:
        # 检查文本是否包含复杂的Markdown语法
        complex_patterns = [
            r'```[\s\S]*?```',  # 代码块
            r'`[^`\n]+`',  # 行内代码
            r'^\s*>',  # 引用
            r'!\[([^\]]*)\]\(([^)]+)\)',  # 图片
            r'<(?:details|summary|pre|div|span|b|i|code|blockquote)[\s\S]*?>'  # HTML标签
        ]
        for pattern in complex_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return False

        # 检查文本长度
        return len(text.split()) < 750  # 假设平均每个token对应1.33个单词

    async def translate_simple_text(self, text: str) -> str | None:
        prompt = f"Translate the following text to English. Preserve any existing formatting or punctuation:"
        content = f"{prompt}\n{text}"
        messages = [{"role": "user", "content": content}]
        logger.info(f"Translating simple text:\n {text}")
        translated, trans_success = await self.rate_limited_do_gpt_translate(self.PROMPT_SYSTEM, messages)
        if not trans_success:
            logger.error("Failed to translate simple text")
            return None
        # 翻译的结果中有可能包含了prompt，需要去掉, 使用正则表达式去掉
        translated = re.sub(rf"^{re.escape(prompt)}\n", "", translated, flags=re.MULTILINE)
        logger.info(f"Translated text:\n {translated}")
        return translated

    def _preprocess_markdown(self, markdown: str) -> Tuple[str, Dict[str, str]]:
        extracts = {}

        patterns = [
            (r'```[\s\S]*?```', 'code block'),
            (r'`[^`\n]+`', 'inline code'),
            (r'<((?:details|summary|pre|div|span|b|i|code|blockquote)(?:\s[^>]*)?)>([\s\S]*?)</\1>', 'HTML tag'),
            (r'\[([^\]]+)\]\(([^)]+)\)', 'link'),
            (r'!\[([^\]]*)\]\(([^)]+)\)', 'image'),
            (r'^\s*>.*$', 'quote')
        ]

        for pattern, desc in patterns:
            if desc == 'HTML tag':
                markdown = self._replace_and_extract_html(pattern, markdown, extracts, desc)
            else:
                markdown = self._replace_and_extract(pattern, markdown, extracts, desc)

        return markdown, extracts

    def _replace_and_extract(self, pattern: str, md: str, extracts: Dict[str, str], desc: str) -> str:
        def repl(match):
            self.placeholder_counter += 1
            placeholder = f"__PLACEHOLDER_{self.placeholder_counter}_{desc}__"
            extracts[placeholder] = match.group(0)
            return placeholder

        return re.sub(pattern, repl, md, flags=re.MULTILINE)

    def _replace_and_extract_html(self, pattern: str, md: str, extracts: Dict[str, str], desc: str) -> str:
        def repl(match):
            tag = match.group(1)
            content = match.group(2)

            # Recursively process nested tags
            content = self._replace_and_extract_html(pattern, content, extracts, desc)

            # Only replace the content if it contains no more HTML tags
            if not re.search(pattern, content):
                self.placeholder_counter += 1
                placeholder = f"__PLACEHOLDER_{self.placeholder_counter}_{desc}__"
                extracts[placeholder] = f"<{tag}>{content}</{tag.split()[0]}>"
                return placeholder
            else:
                return f"<{tag}>{content}</{tag.split()[0]}>"

        return re.sub(pattern, repl, md, flags=re.DOTALL)

    def _split_markdown(self, markdown: str) -> List[str]:
        chunks = []
        current_chunk = []
        current_length = 0

        for line in markdown.split('\n'):
            line_length = len(line)
            if current_length + line_length > self.max_tokens and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_length = 0
            current_chunk.append(line)
            current_length += line_length

        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks

    def _postprocess_markdown(self, translated_md: str, extracts: Dict[str, str]) -> str:
        def replace_placeholders(text):
            for placeholder, original in extracts.items():
                if placeholder in text:
                    # Recursively replace placeholders in the original content
                    original = replace_placeholders(original)
                    text = text.replace(placeholder, original)
            return text

        return replace_placeholders(translated_md)

    async def _translate_chunks(self, chunks: List[str]) -> List[str]:
        async def translate_chunk(chunk):
            prompt = f"Translate the following GitHub Flavored Markdown text to English. Do not change any formatting, placeholders, or Markdown syntax. Preserve all line breaks and spacing:"
            logger.info(f"Translating chunk:\n {chunk}")
            if self.check_english(chunk):
                logger.info("Already English, skip")
                return chunk
            content = f"{prompt}\n{chunk}"
            messages = [{"role": "user", "content": content}]
            translated, trans_success = await self.rate_limited_do_gpt_translate(self.PROMPT_SYSTEM, messages)
            if not trans_success:
                logger.error("Failed to translate chunk")
                return chunk
            translated = re.sub(rf"^{re.escape(prompt)}\n", "", translated, flags=re.MULTILINE)
            logger.info(f"Translated chunk:\n {translated}")
            return translated

        tasks = [translate_chunk(chunk) for chunk in chunks]
        translated_chunks = await asyncio.gather(*tasks)
        return translated_chunks
