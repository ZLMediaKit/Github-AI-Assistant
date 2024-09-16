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
@time:上午11:33
"""
__author__ = 'alex'

import hashlib
import json
import os
from typing import List, Dict, Any

import pydantic

from core.utils.decorators import SingletonDict

MANAGER_DICT = SingletonDict()


class FileDetails(pydantic.BaseModel):
    file_name: str
    code_hash: str
    language: str
    file_path: str
    dependencies: List[str]
    code_elements: List[Dict[str, Any]]


class IndexItem(pydantic.BaseModel):
    file_name: str
    code_hash: str
    language: str
    last_modified: float
    dependencies: List[str]


INDEX_PATH_PREFIX = '.index'
STRUCTURE_PATH_PREFIX = '.structure'


def get_index_path(repo_fullname: str, base_path: str) -> str:
    return os.path.join(base_path, f'{INDEX_PATH_PREFIX}/{repo_fullname}')


def get_structure_path(repo_fullname: str, base_path: str) -> str:
    return os.path.join(base_path, f'{STRUCTURE_PATH_PREFIX}/{repo_fullname}.json')


class IndexManager:
    def __init__(self, repo_fullname: str, base_path: str, source_path: str):
        self.repo_fullname = repo_fullname
        self.base_path = base_path
        self.source_path = source_path
        self.index_path = get_index_path(repo_fullname, base_path)
        self.structure_path = get_structure_path(repo_fullname, base_path)
        self.structure = {}
        self.check_index_exist()
        self.load_structure_from_json()

    def make_full_index(self):
        pass

    def clean_index(self):
        """
        清空索引,删除索引文件
        :return:
        """
        if os.path.exists(self.index_path):
            # 删除目录下所有文件
            for file in os.listdir(self.index_path):
                os.remove(os.path.join(self.index_path, file))

    def get_index_file_name(self, file_name: str) -> str:
        file_name_hash = hashlib.sha256(file_name.encode()).hexdigest()
        return os.path.join(self.index_path, f"{file_name_hash}.json")

    def check_index_exist(self):
        if not os.path.exists(self.index_path):
            os.makedirs(self.index_path)

    def insert_or_update(self, file_detail: FileDetails):
        index_file_name = self.get_index_file_name(file_detail.file_name)
        index_item = IndexItem(
            file_name=file_detail.file_name,
            code_hash=file_detail.code_hash,
            language=file_detail.language,
            last_modified=os.path.getmtime(os.path.join(self.source_path, file_detail.file_name)),
            dependencies=file_detail.dependencies
        )
        with open(index_file_name, 'w') as f:
            f.write(index_item.json())
        self.insert_structure_item(file_detail.file_name)

    def delete(self, file_name: str):
        index_file_name = self.get_index_file_name(file_name)
        if os.path.exists(index_file_name):
            os.remove(index_file_name)
            self.delete_structure_item(file_name)

    def get_index(self, file_name) -> IndexItem | None:
        index_file_name = self.get_index_file_name(file_name)
        if os.path.exists(index_file_name):
            with open(index_file_name, 'r') as f:
                return IndexItem.parse_raw(f.read())
        return None

    def make_structure(self, files: List[str]):
        """
        分析项目结构
        """
        self.structure = {}
        for file_path in files:
            file_name_for_index = os.path.relpath(file_path, self.source_path)
            self._insert_path(file_name_for_index)
        return self.structure

    def _insert_path(self, path: str):
        """
        将路径插入到结构中
        """
        parts = self._split_path(path)
        current = self.structure
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = "file"

    def _split_path(self, path: str) -> List[str]:
        """
        分割路径为目录和文件名
        """
        return path.split(os.sep)

    def _is_directory(self, path: str) -> bool:
        """
        判断路径是否为目录
        """
        return not os.path.splitext(path)[1]

    def delete_structure_item(self, file_path: str) -> bool:
        """
        从结构中删除指定路径的项
        """
        parts = self._split_path(file_path)
        current = self.structure
        for part in parts[:-1]:
            if part not in current:
                return False
            current = current[part]

        if parts[-1] in current:
            del current[parts[-1]]
            return True
        return False

    def insert_structure_item(self, file_path: str) -> bool:
        """
        在指定路径插入新项
        """
        parts = self._split_path(file_path)
        current = self.structure
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        if parts[-1] not in current:
            item_type = "file" if not self._is_directory(file_path) else {}
            current[parts[-1]] = item_type
            return True
        return False

    def save_structure_to_json(self):
        """
        将结构保存为JSON文件
        """
        if not os.path.exists(os.path.dirname(self.structure_path)):
            os.makedirs(os.path.dirname(self.structure_path))
        with open(self.structure_path, 'w') as f:
            json.dump(self.structure, f, indent=2)

    def load_structure_from_json(self):
        """
        从JSON文件加载结构
        """
        if not os.path.exists(self.structure_path):
            self.structure = {}
            return
        with open(self.structure_path, 'r') as f:
            self.structure = json.load(f)


def get_index_manager(repo_fullname: str, base_path: str, source_path: str) -> IndexManager:
    if repo_fullname not in MANAGER_DICT:
        MANAGER_DICT[repo_fullname] = IndexManager(repo_fullname, base_path, source_path)
    return MANAGER_DICT[repo_fullname]
