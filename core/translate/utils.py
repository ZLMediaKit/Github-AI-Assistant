# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/translation_issues).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
import re

import emoji

TRANS_MAGIC = "TRANS_BY_GPT4"
TRANS_DELIMITER = '\n\n'
TRANS_DELIMITER_PR = '---------'


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
