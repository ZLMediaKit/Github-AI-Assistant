# -*- coding:utf-8 -*-
from .utils import wrap_magic, clean_body, already_english, TRANS_MAGIC, TRANS_DELIMITER, TRANS_DELIMITER_PR
from .backend import SimpleSplitGFMTranslator, AdvancedGFMTranslator, BaseGFMTranslator, get_ai_model


def get_translator(translator_type: str, **kwargs) -> BaseGFMTranslator:
    if translator_type == "SimpleSplitGFMTranslator":
        return SimpleSplitGFMTranslator(**kwargs)
    elif translator_type == "AdvancedGFMTranslator":
        return AdvancedGFMTranslator(**kwargs)
    else:
        return SimpleSplitGFMTranslator(**kwargs)

