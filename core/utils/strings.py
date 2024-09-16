# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
import hashlib
import re


def filter_string(byte_string: bytes) -> str:
    """
    过滤字符串中的非法字符, 以及乱码
    :param byte_string: bytes
    :return: str
    """
    # Decode bytes to string
    string = byte_string.decode(errors='ignore')

    # Filter out the garbled text
    string = string.replace('\n', '').replace('\r', '').replace('\t', '')
    string = string.replace('\u200b', '').replace('\xa0', '')
    string = string.replace('\u3000', '').replace('\u2028', '')
    string = string.replace('\u200e', '').replace('\u202a', '')
    string = string.replace('\u200f', '').replace('\u2061', '')
    string = string.replace('\u3000', '').replace('\ufeff', '')
    string = string.replace('\u202c', '').replace('\u2060', '')
    string = string.replace('\u2063', '').replace('\x1a', '')
    string = string.replace('\x00', '').replace('\x01', '')
    string = string.replace('\x02', '').replace('\x03', '')
    string = string.replace('\x04', '').replace('\x05', '')
    string = string.replace('\x06', '').replace('\x07', '')
    string = string.replace('\x08', '').replace('\x09', '')
    string = string.replace('\x0a', '').replace('\x0b', '')
    string = string.replace('\x0c', '').replace('\x0d', '')
    string = string.replace('\x0e', '').replace('\x0f', '')
    string = string.replace('\x10', '').replace('\x11', '')
    string = string.replace('\x12', '').replace('\x13', '')
    string = string.replace('\x14', '').replace('\x15', '')
    string = string.replace('\x16', '').replace('\x17', '')
    string = string.replace('\x18', '').replace('\x19', '')
    string = string.replace('\x1b', '').replace('\x1c', '')
    string = string.replace('\x1d', '').replace('\x1e', '')
    string = string.replace('\x1f', '')
    return string.strip()


def is_ip_address(ip: str) -> bool:
    """
    Check if the string is an IP address
    :param ip:
    :return:
    """

    return bool(re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip))


def get_content_hash(content: str) -> str:
    """
    Get the hash value of the content
    """
    return hashlib.sha256(content.encode()).hexdigest()

