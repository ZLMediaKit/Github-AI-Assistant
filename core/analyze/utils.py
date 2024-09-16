# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
"""
@author:alex
@date:2024/9/15
@time:上午4:00
"""
__author__ = 'alex'

import os

SUPPORTED_LANGUAGES = {
    'python': ['.py'],
    'cpp': ['.cpp', '.hpp'],
    'c': ['.c', '.h']
}

SUPPORTED_LANGUAGES_EXTENSIONS = {ext: lang for lang, exts in SUPPORTED_LANGUAGES.items() for ext in exts}


def get_support_file_language(file_path: str) -> str:
    """
    根据文件扩展名确定编程语言
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in SUPPORTED_LANGUAGES_EXTENSIONS:
        return SUPPORTED_LANGUAGES_EXTENSIONS[ext]
    else:
        return 'unknown'

