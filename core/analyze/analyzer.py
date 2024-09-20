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
@time:上午2:36
"""
__author__ = 'alex'

import ast
import enum
import os
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Set, Tuple, Optional
import clang.cindex


class CodeElementType(enum.Enum):
    FUNCTION = "function"
    CLASS = "class"
    VARIABLE = "variable"
    ENUM = "enum"
    STRUCT = "struct"
    CONSTANT = "constant"
    MACRO = "macro"  # 新增宏类型


class CodeElementAnalyzer(ABC):

    def __init__(self, project_root: str):
        self.project_root = os.path.abspath(project_root)
        self.file_index: Dict[str, str] = {}

    @abstractmethod
    def extract_code_elements(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def analyze_dependencies(self, file_path: str, content: str) -> List[str]:
        pass

    @abstractmethod
    def extract_names_from_patch(self, patch_content: str) -> Tuple[Set[str], Set[str]]:
        pass

    @abstractmethod
    def extract_functions_from_patch(self, patch_content: str) -> Set[str]:
        pass
    @abstractmethod
    def extract_definitions(self, content: str, names: Set[str]) -> Dict[str, str]:
        pass

    def build_file_index(self):
        """
        构建项目文件索引
        """
        for root, _, files in os.walk(self.project_root):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.project_root)
                self.file_index[file] = rel_path

    def find_dependencies(self, file_path: str, includes: List) -> List[str]:
        """
        分析文件的项目内依赖关系

        :param file_path: 当前分析的文件路径
        :param includes: 文件中的所有依赖列表
        :return: 项目内依赖的列表，每个元素是一个元组 (include路径, 实际文件路径或None)
        """

        project_dependencies = []
        if not self.file_index:
            self.build_file_index()
        for include in includes:
            actual_path = self.find_actual_file(include, os.path.dirname(file_path))
            if actual_path:
                # rel_path = os.path.relpath(actual_path, self.project_root)
                project_dependencies.append(actual_path)
            # else:
            #     # 对于找不到的文件，我们仍然记录它，但实际路径为None
            #     print(f"Warning: Cannot find file {include} in project")

        return project_dependencies

    def find_actual_file(self, include_path: str, current_dir: str) -> Optional[str]:
        """
        在项目中查找包含文件的实际路径

        :param include_path: 包含语句中的路径
        :param current_dir: 当前文件的目录
        :return: 实际文件的相对路径，如果找不到则返回None
        """
        # 首先检查相对于当前目录的路径
        full_path = os.path.normpath(os.path.join(current_dir, include_path))
        rel_path = os.path.relpath(full_path, self.project_root)
        if rel_path in self.file_index.values():
            return rel_path

        # 如果没找到，检查文件名是否在索引中
        file_name = os.path.basename(include_path)
        if file_name in self.file_index:
            return self.file_index[file_name]

        return None

    def is_in_project(self, file_path: str) -> bool:
        """
        检查文件是否在项目目录内

        :param file_path: 文件路径
        :return: 如果文件在项目目录内则返回True，否则返回False
        """
        return os.path.abspath(file_path).startswith(self.project_root)


class PythonAnalyzer(CodeElementAnalyzer):
    def extract_code_elements(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        elements = []
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                elements.append({
                    'type': CodeElementType.FUNCTION.value,
                    'name': node.name,
                    'content': ast.get_source_segment(content, node),
                    'file': file_path,
                    'line': node.lineno,
                    'column': node.col_offset
                })
            elif isinstance(node, ast.ClassDef):
                elements.append({
                    'type': CodeElementType.CLASS.value,
                    'name': node.name,
                    'content': ast.get_source_segment(content, node),
                    'file': file_path,
                    'line': node.lineno,
                    'column': node.col_offset
                })
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        elements.append({
                            'type': CodeElementType.VARIABLE.value,
                            'name': target.id,
                            'content': ast.get_source_segment(content, node),
                            'file': file_path,
                            'line': node.lineno,
                            'column': node.col_offset
                        })
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                elements.append({
                    'type': CodeElementType.VARIABLE.value,
                    'name': node.target.id,
                    'content': ast.get_source_segment(content, node),
                    'file': file_path,
                    'line': node.lineno,
                    'column': node.col_offset
                })

        return elements

    def analyze_dependencies(self, file_path: str, content: str) -> List[str]:
        tree = ast.parse(content)
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        # 转换和过滤依赖
        project_dependencies = self.find_dependencies(file_path, imports)
        # 去重并返回
        return list(set(project_dependencies))

    def extract_names_from_patch(self, patch_content: str) -> Tuple[Set[str], Set[str]]:
        tree = ast.parse(patch_content)
        functions = set()
        variables = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.add(node.name)
            elif isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    variables.add(node.id)

        return functions, variables

    def extract_functions_from_patch(self, patch_content: str) -> Set[str]:
        # 用于存储提取的信息
        extracted_info = set()

        # 正则表达式模式
        type_pattern = r'\b([A-Z][a-zA-Z0-9_]*)\b'
        function_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        variable_pattern = r'\b([a-z_][a-zA-Z0-9_]*)\b'

        # 逐行分析 patch 内容
        for line in patch_content.split('\n'):
            # 提取类型（假设以大写字母开头）
            types = re.findall(type_pattern, line)
            extracted_info.update(types)

            # 提取函数（假设后面跟着括号）
            functions = re.findall(function_pattern, line)
            extracted_info.update(functions)
        return extracted_info

    def extract_definitions(self, content: str, names: Set[str]) -> Dict[str, str]:
        tree = ast.parse(content)
        definitions = {}

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in names:
                definitions[node.name] = ast.get_source_segment(content, node)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in names:
                        definitions[target.id] = ast.get_source_segment(content, node)

        return definitions


class CppAnalyzer(CodeElementAnalyzer):
    def __init__(self, project_root: str):
        super().__init__(project_root)
        self.index = clang.cindex.Index.create()

    def extract_code_elements(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        tu = self.index.parse(file_path, args=['-std=c++11'])
        root = tu.cursor
        elements = self._extract_elements(root, file_path)
        elements.extend(self._extract_macros(tu, file_path))
        return elements

    def _extract_elements(self, node, file_path: str, depth: int = 0) -> List[Dict[str, Any]]:
        if depth > 5:  # 限制递归深度
            return []

        elements = []
        for child in node.get_children():
            if not self._is_from_project(child, file_path):
                continue

            element_type = self._get_element_type(child.kind)
            if element_type:
                element_content = self._get_element_content(child)
                if element_content:
                    elements.append({
                        'type': element_type.value,
                        'name': child.spelling,
                        'content': element_content,
                        'file': child.location.file.name if child.location.file else file_path,
                        'line': child.location.line,
                        'column': child.location.column
                    })

            # 递归处理子元素
            elements.extend(self._extract_elements(child, file_path, depth + 1))

        return elements

    def _extract_macros(self, translation_unit, file_path: str) -> List[Dict[str, Any]]:
        macros = []
        for cursor in translation_unit.cursor.get_children():
            if cursor.kind == clang.cindex.CursorKind.MACRO_DEFINITION:
                if self._is_from_project(cursor, file_path):
                    macro_content = self._get_macro_content(cursor)
                    macros.append({
                        'type': CodeElementType.MACRO.value,
                        'name': cursor.spelling,
                        'content': macro_content,
                        'file': cursor.location.file.name,
                        'line': cursor.location.line,
                        'column': cursor.location.column
                    })
        return macros

    def _get_macro_content(self, cursor):
        tokens = list(cursor.get_tokens())
        if len(tokens) > 1:  # 第一个 token 是宏名称，我们需要剩余的部分
            content = ' '.join(token.spelling for token in tokens[1:])
            return f"#define {cursor.spelling} {content}"
        return f"#define {cursor.spelling}"

    def _get_element_type(self, kind) -> CodeElementType | None:
        if kind in [clang.cindex.CursorKind.FUNCTION_DECL, clang.cindex.CursorKind.CXX_METHOD]:
            return CodeElementType.FUNCTION
        elif kind == clang.cindex.CursorKind.CLASS_DECL:
            return CodeElementType.CLASS
        elif kind == clang.cindex.CursorKind.ENUM_DECL:
            return CodeElementType.ENUM
        elif kind == clang.cindex.CursorKind.STRUCT_DECL:
            return CodeElementType.STRUCT
        # elif kind in [clang.cindex.CursorKind.VAR_DECL, clang.cindex.CursorKind.FIELD_DECL]:
        #     return CodeElementType.VARIABLE
        # elif kind == clang.cindex.CursorKind.ENUM_CONSTANT_DECL:
        #     return CodeElementType.CONSTANT
        return None

    def _is_from_project(self, node, current_file: str) -> bool:
        if node.location.file is None:
            return False
        file_path = os.path.abspath(node.location.file.name)
        return file_path.startswith(self.project_root) and (
                file_path == current_file or not file_path.endswith(('.h', '.hpp')))

    def _get_element_content(self, node) -> str:
        try:
            tokens = list(node.get_tokens())
            if tokens:
                # 过滤掉可能的系统调用或外部库调用
                content = ' '.join(token.spelling for token in tokens
                                   if not self._is_likely_external(token.spelling))
                return content if content.strip() else ""
            else:
                return node.spelling if not self._is_likely_external(node.spelling) else ""
        except AttributeError:
            return node.spelling if not self._is_likely_external(node.spelling) else ""

    def _is_likely_external(self, content: str) -> bool:
        # 这个列表可以根据项目需要进行调整
        external_indicators = ['std::', 'boost::', 'extern ', '#include <']
        return any(indicator in content for indicator in external_indicators)

    def analyze_dependencies(self, file_path: str, content: str) -> List[str]:
        """
        分析文件的依赖关系，并过滤掉非项目内的依赖

        :param file_path: 当前分析的文件路径
        :param content: 文件内容
        :param base_path: 项目的基础路径
        :return: 项目内的依赖列表
        """
        # 查找所有的 #include 语句
        includes = re.findall(r'#include\s*[<"]([^>"]+)[>"]', content)

        # 转换和过滤依赖
        project_dependencies = self.find_dependencies(file_path, includes)
        # 对于每个头文件依赖，尝试找到对应的实现文件
        implementation_dependencies = []
        for dep in project_dependencies:
            impl_file = self.find_implementation_file(dep)
            if impl_file:
                implementation_dependencies.append(impl_file)

        # 合并头文件和实现文件的依赖，去重并返回
        all_dependencies = list(set(project_dependencies + implementation_dependencies))
        return all_dependencies

    def find_implementation_file(self, header_path: str) -> Optional[str]:
        """
        根据头文件路径查找对应的实现文件

        :param header_path: 头文件的相对路径
        :return: 实现文件的相对路径，如果找不到则返回None
        """
        implementation_extensions = ['.cpp', '.cxx', '.cc', '.c']
        base_name = os.path.splitext(header_path)[0]

        for ext in implementation_extensions:
            impl_path = base_name + ext
            if impl_path in self.file_index.values():
                return impl_path

        # 如果在同一目录下找不到，尝试在整个项目中查找
        file_name = os.path.basename(base_name)
        for ext in implementation_extensions:
            impl_file = file_name + ext
            if impl_file in self.file_index:
                return self.file_index[impl_file]

        return None

    def extract_names_from_patch(self, patch_content: str) -> Tuple[Set[str], Set[str]]:
        tu = self.index.parse('tmp.cpp', unsaved_files=[('tmp.cpp', patch_content)], args=['-std=c++11'])
        functions = set()
        variables = set()

        def visit_node(node):
            if node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
                functions.add(node.spelling)
            elif node.kind == clang.cindex.CursorKind.VAR_DECL:
                variables.add(node.spelling)

            for child in node.get_children():
                visit_node(child)

        for child in tu.cursor.get_children():
            visit_node(child)

        # visit_node(tu.cursor)
        return functions, variables

    def extract_functions_from_patch(self, patch_content: str) -> Set[str]:
        functions = set()
        variables = set()

        # 正则表达式模式
        # 匹配函数定义或声明，可能包含命名空间
        function_def_pattern = r'(?:(?:\w+::)*\w+\s+)+(\w+(?:::\w+)*)\s*\([^)]*\)\s*(?:const)?\s*(?:{\s*)?'
        # 匹配潜在的函数调用或控制结构
        potential_call_pattern = r'(\w+(?:::\w+)*)\s*\([^)]*\)'
        # 匹配变量声明，可能包含命名空间
        variable_pattern = r'(?:(?:\w+::)*\w+\s+)+((?:\w+::)*\w+)\s*(?:=|;)'

        # 系统函数和关键字列表（可以根据需要扩展）
        system_functions = {'std::', 'boost::', 'printf', 'scanf', 'malloc', 'free', 'new', 'delete'}
        control_structures = {'if', 'while', 'for', 'switch', 'catch'}

        # 提取函数定义
        for match in re.finditer(function_def_pattern, patch_content):
            func_name = match.group(1)
            if self._is_valid_function(func_name, system_functions, control_structures):
                functions.add(func_name)

        # 提取潜在的函数调用
        for match in re.finditer(potential_call_pattern, patch_content):
            func_name = match.group(1)
            if self._is_valid_function(func_name, system_functions, control_structures):
                # 检查是否为控制结构
                prev_chars = patch_content[max(0, match.start() - 20):match.start()].split()
                if prev_chars and prev_chars[-1] not in control_structures:
                    functions.add(func_name)

        # 提取变量名
        for match in re.finditer(variable_pattern, patch_content):
            var_name = match.group(1)
            if self._is_valid_function(var_name, system_functions, control_structures):
                variables.add(var_name)

        return functions

    def _is_valid_function(self, name: str, system_functions: Set[str], control_structures: Set[str]) -> bool:
        """
        检查名称是否为有效的函数名（不是系统函数或控制结构）

        :param name: 要检查的名称
        :param system_functions: 系统函数集合
        :param control_structures: 控制结构集合
        :return: 如果是有效的函数名则返回True，否则返回False
        """
        return not any(name.startswith(sys_func) for sys_func in system_functions) and name not in control_structures


    def extract_definitions(self, content: str, names: Set[str]) -> Dict[str, str]:
        tu = self.index.parse('tmp.cpp', unsaved_files=[('tmp.cpp', content)])
        definitions = {}

        def visit_node(node):
            if node.spelling in names:
                if node.kind == clang.cindex.CursorKind.FUNCTION_DECL:
                    definitions[node.spelling] = content[node.extent.start.offset:node.extent.end.offset]
                elif node.kind == clang.cindex.CursorKind.VAR_DECL:
                    definitions[node.spelling] = content[node.extent.start.offset:node.extent.end.offset]

            for child in node.get_children():
                visit_node(child)

        visit_node(tu.cursor)
        return definitions
