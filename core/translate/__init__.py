# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
from .backend import SimpleSplitGFMTranslator, AdvancedGFMTranslator, BaseGFMTranslator
from .utils import wrap_magic, clean_body, already_english, TRANS_MAGIC, TRANS_DELIMITER, TRANS_DELIMITER_PR, \
    TRANSLATION_MARK, BATCH_SIZE, find_cpp_files, extract_comments, is_already_translated, format_translated_comment,\
    validate_code


def get_translator(translator_type: str, **kwargs) -> BaseGFMTranslator:
    if translator_type == "SimpleSplitGFMTranslator":
        return SimpleSplitGFMTranslator(**kwargs)
    elif translator_type == "AdvancedGFMTranslator":
        return AdvancedGFMTranslator(**kwargs)
    else:
        return SimpleSplitGFMTranslator(**kwargs)

