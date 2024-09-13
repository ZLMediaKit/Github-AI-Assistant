# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
import os
import re

import emoji

TRANS_MAGIC = "TRANS_BY_GITHUB_AI_ASSISTANT"
TRANS_DELIMITER = '\n\n'
TRANS_DELIMITER_PR = '---------'
TRANSLATION_MARK = "AUTO-TRANSLATED"

# 每次API调用翻译的注释数量
BATCH_SIZE = 30


def already_english(string):
    for c in string:
        if len(c) != len(c.encode('utf-8')) and emoji.emoji_count(c) == 0:
            return False
    return True


def wrap_magic(body, extra_delimiter='', original_body=''):
    if not body:
        return None
    if TRANS_MAGIC in body:
        return body
    magic = ''
    if extra_delimiter != '':
        magic = f"{TRANS_DELIMITER}{extra_delimiter}"
    if original_body != '':
        magic = f"{TRANS_DELIMITER}>{original_body}"
    magic = f"{magic}{TRANS_DELIMITER}`{TRANS_MAGIC}`"

    return f"{body}{magic}"


def clean_body(body: str, full: bool = False) -> str:
    """
    清理文本, 使用正则过滤掉markdown的注释内容
    :param full:
    :param body:
    :return:
    """
    body = re.sub(r'<!--.*?-->', '', body, flags=re.DOTALL)
    if full:
        # # 清除<pre>标签中的内容
        body = re.sub(r'<pre>.*?</pre>', '', body, flags=re.DOTALL)
        # # 过滤掉所有的html标签, 保留标签内的内容
        body = re.sub(r'<.*?>', '', body)
    return body


def find_cpp_files(directory):
    cpp_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.cpp', '.h', '.c')):
                cpp_files.append(os.path.join(root, file))
    return cpp_files


def extract_comments(content):
    # 改进的正则表达式，可以捕获缩进和不同的注释样式
    pattern = r'^([ \t]*)(/\*\*?[\s\S]*?\*/|//.*?$)'
    return re.finditer(pattern, content, re.MULTILINE)


def is_already_translated(comment):
    return TRANSLATION_MARK in comment


def format_translated_comment(original: str, translation, indentation, comment_hash):
    if original.lstrip().startswith('//'):
        # 单行注释
        translation = re.sub(r'^//\s*', '', translation)
        # 判断original中//和接下去的字符串之间是否有空格, 没有就添加一个空格
        if original.strip().split('//')[1][0] != ' ':
            # 需要插入一个空格
            original = original.replace('//', '// ', 1)
        return f"{original}  [{TRANSLATION_MARK}:{comment_hash}]\n{indentation}// {translation.strip()}"
    else:
        # 多行注释
        lines = original.split('\n')
        if len(lines) > 1:
            # 找到注释的结束位置
            end_index = next(i for i, line in enumerate(lines) if '*/' in line)

            # 准备翻译后的行
            translation_lines = [f"{indentation} {line.strip().replace('/* ', '*')}" for line in
                                 translation.split('\n')]
            translation_lines.append(f"{indentation} * [{TRANSLATION_MARK}:{comment_hash}]")

            # 在原始注释的最后一行之前插入翻译
            result = lines[:end_index] + translation_lines + [lines[end_index]]
            return '\n'.join(result)
        else:
            # 单行的多行注释
            return f"{original[:-2]}\n{indentation} {translation.strip()}\n{indentation} * [{TRANSLATION_MARK}:{comment_hash}]\n{indentation} */"


def validate_code(content):
    stack = []
    for i, char in enumerate(content):
        if char in "({[":
            stack.append((char, i))
        elif char in ")}]":
            if not stack:
                return False, f"In position {i}, there is an unmatched closing bracket '{char}'"
            last_open, _ = stack.pop()
            if (char == ")" and last_open != "(") or \
                    (char == "}" and last_open != "{") or \
                    (char == "]" and last_open != "["):
                return False, f"Unmatched brackets '{last_open}' and '{char}' at position {i}"
    if stack:
        last_open, pos = stack[-1]
        return False, f"Unmatched brackets '{last_open}' at position {pos}"
    return True, ""
