# -*- coding:utf-8 -*-

#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
"""
@author:alex
@date:2024/9/13
@time:上午7:53
"""
__author__ = 'alex'

from typing import Optional, Tuple

BOM_MARKS = {
    'UTF-8': b'\xef\xbb\xbf',
    'UTF-16 LE': b'\xff\xfe',
    'UTF-16 BE': b'\xfe\xff',
    'UTF-32 LE': b'\xff\xfe\x00\x00',
    'UTF-32 BE': b'\x00\x00\xfe\xff'
}


def has_bom(file_path: str) -> Optional[bytes]:
    bom_marks = {
        b'\xef\xbb\xbf': 'UTF-8',
        b'\xff\xfe': 'UTF-16 LE',
        b'\xfe\xff': 'UTF-16 BE',
        b'\xff\xfe\x00\x00': 'UTF-32 LE',
        b'\x00\x00\xfe\xff': 'UTF-32 BE'
    }
    with open(file_path, 'rb') as file:
        first_bytes = file.read(4)
    for bom, encoding in bom_marks.items():
        if first_bytes.startswith(bom):
            return bom
    return None


def read_file(file_path: str) -> Tuple[str, Optional[bytes]]:
    bom = has_bom(file_path)
    with open(file_path, 'r', encoding='utf-8-sig') as file:
        content = file.read()
    return content, bom


def write_file(file_path: str, content: str, bom: Optional[bytes]) -> None:
    with open(file_path, 'w', encoding='utf-8') as file:
        if bom:
            file.write(bom.decode('utf-8'))
        file.write(content)


def read_file_without_bom(file_path: str, encoding: str) -> str:
    bom = has_bom(file_path)
    with open(file_path, 'r', encoding=encoding) as file:
        content = file.read()
    if bom:
        content = content.lstrip(bom.decode(encoding))
    return content


def write_file_with_bom(file_path: str, content: str, encoding: str) -> None:
    bom = BOM_MARKS.get(encoding.upper())
    with open(file_path, 'w', encoding=encoding) as file:
        if bom:
            file.write(bom.decode(encoding))
        file.write(content)
