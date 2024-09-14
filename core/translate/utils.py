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
CODE_COMMENTS_SUFFIX = ('.cpp', '.h', '.c', '.hpp')


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
            if file.endswith(CODE_COMMENTS_SUFFIX):
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
        if not original.strip().startswith("// "):
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
    ifdef_stack = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, 1):
        in_string = False
        string_char = None
        for i, char in enumerate(line):
            if char in "\"'":
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None
            elif not in_string:
                if char in "({[":
                    stack.append((char, line_num, i))
                elif char in ")}]":
                    if not stack:
                        context = get_context(lines, line_num, i)
                        return False, f"In line {line_num}, position {i} there is an unmatched" \
                                      f" closing bracket '{char}':\n{context}"
                    last_open, open_line, open_pos = stack.pop()
                    if (char == ")" and last_open != "(") or \
                            (char == "}" and last_open != "{") or \
                            (char == "]" and last_open != "["):
                        context = get_context(lines, line_num, i)
                        return False, f"In line {line_num}, position {i} the bracket '{char}' does not match the" \
                                      f" bracket '{last_open}' at line {open_line}, position {open_pos}:\n{context}"

        # 处理 #if, #ifdef, #ifndef, #else, #elif, #endif
        stripped_line = line.strip()
        if stripped_line.startswith('#if') or stripped_line.startswith('#ifdef') or stripped_line.startswith('#ifndef'):
            ifdef_stack.append(line_num)
        elif stripped_line.startswith('#endif'):
            if not ifdef_stack:
                context = get_context(lines, line_num, 0)
                return False, f"In line {line_num} there is an extra #endif:\n{context}"
            ifdef_stack.pop()
        elif stripped_line.startswith('#else') or stripped_line.startswith('#elif'):
            if not ifdef_stack:
                context = get_context(lines, line_num, 0)
                return False, f"In line {line_num} there is an isolated {stripped_line.split()[0]}:\n{context}"

    if stack:
        last_open, line_num, pos = stack[-1]
        context = get_context(lines, line_num, pos)
        return False, f"In line {line_num}, position {pos} there is an unmatched opening bracket '{last_open}':\n{context}"
    if ifdef_stack:
        line_num = ifdef_stack[-1]
        context = get_context(lines, line_num, 0)
        return False, f"In line {line_num} there is a condition directive without a matching #endif:\n{context}"
    return True, ""


def get_context(lines, line_num, pos, context_lines=3):
    start = max(0, line_num - context_lines - 1)
    end = min(len(lines), line_num + context_lines)
    context = lines[start:end]

    if start > 0:
        context.insert(0, "...")
    if end < len(lines):
        context.append("...")

    highlight_line = line_num - start - 1
    context[highlight_line] = context[highlight_line][:pos] + ">>>" + context[highlight_line][pos:] + "<<<"

    return '\n'.join(f"{i + start + 1}: {line}" for i, line in enumerate(context))
