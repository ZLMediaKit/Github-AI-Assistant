# -*- coding:utf-8 -*-

#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#

"""
@author:alex
@date:2024/9/11
@time:上午3:21
"""
__author__ = 'alex'

import os
import re
from typing import List, Tuple

import httpx

from core import translate
from core.analyze import review
from core.log import logger
from core.utils import github

REVIEWS_FILES_EXTENSIONS = ['.py', '.go', '.java', '.js', '.ts', '.html', '.css', '.vue', '.c', '.cpp', '.h', '.hpp',
                            '.cs', '.swift', '.php', '.rb', '.sh']


def detect_language(diff: str, file_ex: str) -> str:
    """
    基于文件扩展名或内容特征检测编程语言
    """
    extensions = {
        '.py': 'python',
        '.js': 'javascript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.go': 'go',
        '.rb': 'ruby',
        '.php': 'php',
    }

    if file_ex in extensions:
        return extensions[file_ex]
    # 检查文件扩展名
    file_pattern = re.compile(r'diff --git a/.*(\.\w+)')
    match = file_pattern.search(diff)
    if match:
        ext = match.group(1)
        return extensions.get(ext, 'unknown')

    # 基于内容特征检测
    if 'def ' in diff or 'import ' in diff:
        return 'python'
    if 'function ' in diff or 'var ' in diff:
        return 'javascript'
    if 'public class ' in diff:
        return 'java'
    if '#include' in diff:
        return 'cpp'

    return 'unknown'


def remove_comments(code: str, language: str) -> str:
    """
    根据编程语言移除代码中的注释
    """
    if language == 'python':
        # 移除Python的单行和多行注释
        code = re.sub(r'#.*', '', code)
        code = re.sub(r'"""[\s\S]*?"""', '', code)
    elif language in ['javascript', 'java', 'cpp', 'c']:
        # 移除C风格的单行和多行注释
        code = re.sub(r'//.*', '', code)
        code = re.sub(r'/\*[\s\S]*?\*/', '', code)
        code = re.sub(r'^[\s\+\-]*\*[^;]*$', '', code, flags=re.MULTILINE)
    elif language == 'ruby':
        # 移除Ruby的注释
        code = re.sub(r'#.*', '', code)
        code = re.sub(r'=begin[\s\S]*?=end', '', code)
    elif language == 'go':
        # 移除Go的注释
        code = re.sub(r'//.*', '', code)
        code = re.sub(r'/\*[\s\S]*?\*/', '', code)
    elif language == 'php':
        # 移除PHP的注释
        code = re.sub(r'//.*', '', code)
        code = re.sub(r'#.*', '', code)
        code = re.sub(r'/\*[\s\S]*?\*/', '', code)

    return code


def parse_diff(diff: str) -> List[Tuple[str, str]]:
    """
    解析diff，返回变更前后的代码对
    """
    changes = []
    current_old = []
    current_new = []

    for line in diff.splitlines():
        if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
            continue
        elif line.startswith('-'):
            current_old.append(line[1:])
        elif line.startswith('+'):
            current_new.append(line[1:])
        else:
            if current_old or current_new:
                changes.append(('\n'.join(current_old), '\n'.join(current_new)))
                current_old = []
                current_new = []

    if current_old or current_new:
        changes.append(('\n'.join(current_old), '\n'.join(current_new)))

    return changes


def is_significant_change(diff: str, file_file_extension: str) -> bool:
    """
    判断代码变更是否值得进行AI审核
    :param file_file_extension:
    :param diff: 代码差异
    :return: 是否值得审核
    """
    language = detect_language(diff, file_file_extension)
    changes = parse_diff(diff)

    significant_changes = 0
    total_changes = 0

    for old_code, new_code in changes:
        old_code = remove_comments(old_code, language)
        new_code = remove_comments(new_code, language)

        old_lines = [line for line in old_code.splitlines() if line.strip()]
        new_lines = [line for line in new_code.splitlines() if line.strip()]

        total_changes += max(len(old_lines), len(new_lines))
        if len(old_lines) == 0 and len(new_lines) == 0:
            continue
        # 检查是否只是变量重命名
        if len(old_lines) == len(new_lines):
            rename_pattern = re.compile(r'\b(\w+)\b')
            old_words = set(rename_pattern.findall(' '.join(old_lines)))
            new_words = set(rename_pattern.findall(' '.join(new_lines)))
            if len(old_words) == len(new_words) and len(old_words.symmetric_difference(new_words)) <= 2:
                continue

        significant_changes += max(len(old_lines), len(new_lines))

    # 如果显著变更的行数少于5行或占总变更的20%以下，则不进行审核
    return significant_changes >= 5 and (significant_changes / total_changes) > 0.2


async def review_file(file_detail: dict, repo_name: str, commit_message: str, commit_sha: str,
                      client: httpx.AsyncClient) -> str | None:
    filename = file_detail['filename']
    file_patch = file_detail.get('patch', None)
    file_status = file_detail['status']
    file_extension = os.path.splitext(filename)[1]
    if file_extension not in REVIEWS_FILES_EXTENSIONS:
        return None
    if file_status not in ['added', 'modified']:
        return None
    # if file_patch:
    #     if not is_significant_change(file_patch, file_extension):
    #         logger.info("Skip review for file %s", filename)
    #         return None
    logger.info(f"Review file {filename}")
    file_content = await github.get_file_content(repo_name, filename, commit_sha, client)
    review_result = await review.do_ai_review(filename, commit_message, file_status, file_content, file_patch, repo_name)
    return translate.wrap_magic(review_result)


async def review_commit(repo_name, commit_sha):
    logger.info(f"Review commit {commit_sha} in {repo_name}")
    async with httpx.AsyncClient() as client:
        commit_data = await github.get_commit(repo_name, commit_sha, client)
        logger.info(f"Get commit data: {commit_data}")
        commit_message = commit_data['commit']['message']
        for file in commit_data['files']:
            review_result = await review_file(file, repo_name, commit_message, commit_sha, client)
            if not review_result:
                continue
            # 提交评论
            body = f"AI Review for {file['filename']}:\n\n{review_result}"
            await github.create_commit_comment(repo_name, commit_sha, body, client)


async def review_pull_request(repo_name, pr_number, commit_sha, commit_message):
    logger.info(f"Review pull request {pr_number} in {repo_name}")
    async with httpx.AsyncClient() as client:
        # 获取PR文件
        files = await github.get_pr_files(repo_name, pr_number, client)
        logger.info(f"Get PR files: {files}")
        for file in files:
            review_result = await review_file(file, repo_name, commit_message, commit_sha, client)
            if not review_result:
                continue
            # 提交评论
            comment_data = {
                "body": f"AI Review for {file['filename']}:\n\n{review_result}",
                "commit_id": commit_sha,
                "path": file['filename'],
                "subject_type": "file"
            }
            # print(comment_data)
            await github.create_pr_comment(repo_name, pr_number, comment_data, client)


async def review_commits(repo_name, commits):
    for commit in commits:
        await review_commit(repo_name, commit['id'])


async def review_specific_commit(commit_url: str):
    repo_name, commit_sha = github.parse_commit_url(commit_url)
    await review_commit(repo_name, commit_sha)


async def review_specific_pr(pr_url: str):
    repo_detail = github.parse_pullrequest_url(pr_url)
    pr_data = await github.get_pullrequest(repo_detail.get_repo_fullname(), repo_detail.number)
    head_sha = pr_data['head']['sha']
    commit_message = f"{pr_data['title']}\n\n{pr_data.get('body', '')}"
    await review_pull_request(repo_detail.get_repo_fullname(), repo_detail.number, head_sha, commit_message)

