# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#

import httpx
from sanic.log import logger

from apps import trans, review
from core import translate, settings
from core.exception import GithubGraphQLException
from core.translate.utils import CODE_COMMENTS_SUFFIX
from core.utils import github

TRANSLATE_BRANCH_PREFIX = "translate-comments-"


async def handle_merged_pr(repo_name, pr_number):
    # 检查是否已经 fork 了仓库
    if not settings.get_github_username():
        logger.info(f"No github username, skip")
        return
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        # 获取PR文件
        pr_files = await github.get_pr_files(repo_name, pr_number, client)
        logger.info(f"Get PR files: {pr_files}")
        is_need_translate = False
        for file in pr_files:
            # 暂时只支持c/c++
            if file['filename'].endswith(CODE_COMMENTS_SUFFIX):
                is_need_translate = True
                break
        if not is_need_translate:
            return
        repo_detail = await github.get_repo_detail(repo_name, client)
        base_branch = repo_detail['default_branch']
        if repo_name.split("/")[0] != settings.get_github_username():
            is_forked = await github.is_repo_exist(settings.get_github_username(), repo_name.split("/")[1])
            fork_name = f'{settings.get_github_username()}/{repo_name.split("/")[1]}'
        else:
            is_forked = True
            fork_name = None
        if not is_forked:
            await github.fork_repo(repo_name, client)
        if fork_name:
            await github.sync_repo(fork_name, base_branch, client)
        else:
            fork_name = repo_name

        # 创建新分支
        new_branch = f'{TRANSLATE_BRANCH_PREFIX}pr-{pr_number}'
        has_created_branch = False
        translated_files = []
        for file in pr_files:
            if not file['filename'].endswith(CODE_COMMENTS_SUFFIX):
                continue
            file_content = await github.get_file_content_by_raw_url(file['raw_url'], client)
            translated_content, translated = await trans.process_source_file(file['raw_url'], file_content)
            if not translated_content:
                continue
            if not has_created_branch:
                has_created_branch = True
                await github.create_branch(fork_name, base_branch, new_branch, client)
            await github.update_file(fork_name, file['filename'],
                                     f'Translate comments in {file["filename"]}',
                                     translated_content, new_branch, client)
            translated_files.append(file['filename'])

        if translated_files:
            # 创建 PR
            await github.create_pr(repo_name, new_branch, f'Translated comments for PR #{pr_number}',
                                   f'This PR contains translated comments for the merged PR #{pr_number}',
                                   base_branch, client)


async def handle_merged_push(repo_name, commits):
    if not settings.get_github_username():
        logger.info(f"No github username, skip")
        return
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        is_need_translate = False
        for commit in commits:
            for file in commit['added'] + commit['modified']:
                if file.endswith(CODE_COMMENTS_SUFFIX):
                    is_need_translate = True
                    break
        if not is_need_translate:
            return
        repo_detail = await github.get_repo_detail(repo_name, client)
        base_branch = repo_detail['default_branch']
        # 检查是否已经 fork 了仓库
        if repo_name.split("/")[0] != settings.get_github_username():
            is_forked = await github.is_repo_exist(settings.get_github_username(), repo_name.split("/")[1])
            fork_name = f'{settings.get_github_username()}/{repo_name.split("/")[1]}'
        else:
            is_forked = True
            fork_name = None
        if not is_forked:
            await github.fork_repo(repo_name, client)
        if fork_name:
            await github.sync_repo(fork_name, base_branch, client)
        else:
            fork_name = repo_name
        # 创建新分支
        new_branch = f'{TRANSLATE_BRANCH_PREFIX}push-{commits[-1]["id"][:7]}'
        has_created_branch = False
        translated_files = []
        for commit in commits:
            for file in commit['added'] + commit['modified']:
                if not file['filename'].endswith(CODE_COMMENTS_SUFFIX):
                    continue
                file_content = await github.get_file_content(repo_name, file, commit['id'], client)
                translated_content, translated = await trans.process_source_file(file, file_content)
                if not translated_content:
                    continue
                if not has_created_branch:
                    has_created_branch = True
                    await github.create_branch(fork_name, base_branch, new_branch, client)
                await github.update_file(fork_name, file,
                                         f'Translate comments in {file}',
                                         translated_content, new_branch, client)
                translated_files.append(file)

        if translated_files:
            # 创建 PR
            await github.create_pr(repo_name, new_branch, f'Translated comments for push {commits[-1]["id"][:7]}',
                                   f'This PR contains translated comments for the recent push', base_branch, client)


async def issues_handler(action: str, data, event, delivery, headers):
    if action != 'opened':
        logger.info(f"Thread: {delivery}: Ignore action {action}")
    else:
        title = data['issue']['title']
        number = data['issue']['number']
        html_url = data['issue']['html_url']
        logger.info(f"Thread: {delivery}: Got an issue #{number} {html_url} {title}")
        if not settings.TRANSLATION_MODEL.api_key:
            logger.info(f"Thread: {delivery}: No translation model, skip")
            return
        result = await trans.trans_issues(html_url)


async def issue_comment_handler(action: str, data, event, delivery, headers):
    if action != 'created':
        logger.info(f"Thread: {delivery}: Ignore action {action}")
    else:
        html_url = data['comment']['html_url']
        issue_url = data['issue']['html_url']
        node_id = data['comment']['node_id']
        body = data['comment']['body']
        logger.info(f"Thread: {delivery}: Got a comment {html_url} of {issue_url} {node_id} {body}")
        if translate.TRANS_MAGIC in body:
            has_translated_by_gpt = True
            logger.info("Already translated, skip")
            return has_translated_by_gpt
        translator = translate.get_translator(settings.get_translator(),
                                              max_tokens=settings.TRANSLATION_MODEL.max_input_tokens)
        translated_body, has_translated_by_gpt, real_translated = await translator.translate(body)
        if real_translated:
            logger.info(f"Thread: {delivery}: Body:\n{translated_body}\n")
            try:
                await github.update_issue_comment(node_id, translate.wrap_magic(translated_body, original_body=body))
                logger.info(f"Thread: {delivery}: Updated ok")
            except GithubGraphQLException as e:
                if e.is_forbidden():
                    logger.error(
                        f"Thread: {delivery}: Warning!!! Ignore update comment {node_id} failed, forbidden, {e.errors}")
                else:
                    logger.exception(f"Thread: {delivery}: Error!!! Update comment {node_id} failed, {e.errors}")
                    raise e


async def discussion_handler(action: str, data, event, delivery, headers):
    if action != 'created':
        logger.info(f"Thread: {delivery}: Ignore action {action}")
    else:
        html_url = data['discussion']['html_url']
        number = data['discussion']['number']
        title = data['discussion']['title']
        logger.info(f"Thread: {delivery}: Got a discussion #{number} {html_url} {title}")
        result = await trans.trans_discussion(html_url)


async def discussion_comment_handler(action: str, data, event, delivery, headers):
    if action != 'created':
        logger.info(f"Thread: {delivery}: Ignore action {action}")
    else:
        html_url = data['comment']['html_url']
        discussion_url = data['discussion']['html_url']
        node_id = data['comment']['node_id']
        body = data['comment']['body']
        logger.info(f"Thread: {delivery}: Got a comment {html_url} of {discussion_url} {node_id} {body}")
        if translate.TRANS_MAGIC in body:
            has_translated_by_gpt = True
            logger.info("Already translated, skip")
            return has_translated_by_gpt
        translator = translate.get_translator(settings.get_translator(),
                                              max_tokens=settings.TRANSLATION_MODEL.max_input_tokens)
        translated_body, has_translated_by_gpt, real_translated = await translator.translate(body)
        if real_translated:
            logger.info(f"Thread: {delivery}: Body:\n{translated_body}\n")
            try:
                await github.update_discussion_comment(node_id,
                                                       translate.wrap_magic(translated_body, original_body=body))
                logger.info(f"Thread: {delivery}: Updated ok")
            except GithubGraphQLException as e:
                if e.is_forbidden():
                    logger.error(
                        f"Thread: {delivery}: Warning!!! Ignore update comment {node_id} failed, forbidden, {e.errors}")
                else:
                    logger.exception(f"Thread: {delivery}: Error!!! Update comment {node_id} failed, {e.errors}")
                    raise e


async def pull_request_handler(action: str, payload, event, delivery, headers):
    if action == 'closed' and payload['pull_request']['merged']:
        repo_name = payload['repository']['full_name']
        pr_number = payload['number']
        try:
            await handle_merged_pr(repo_name, pr_number)
        except Exception as e:
            logger.exception(f"Thread: {delivery}: Error!!! Handle merged PR failed, {e}")
        return
    if action not in ["opened", "synchronize"]:
        logger.info(f"Thread: {delivery}: Ignore action {action}")
        return
    else:
        html_url = payload['pull_request']['html_url']
        number = payload['pull_request']['number']
        title = payload['pull_request']['title']
        body = payload['pull_request'].get('body', "")
        head = payload['pull_request']['head']
        logger.info(f"Thread: {delivery}: Got a pull request #{number} {html_url} {title}\n{body}")
        if head.get("ref", "").startswith(TRANSLATE_BRANCH_PREFIX):
            logger.info(f"Thread: {delivery}: Skip translated PR")
            return
        result = await trans.trans_pr(html_url)
    repo_name = payload["repository"]["full_name"]
    pr_number = payload["number"]
    head_sha = payload["pull_request"]["head"]["sha"]
    if not settings.REVIEW_MODEL.api_key:
        logger.info(f"Thread: {delivery}: No review model, skip")
        return

    await review.review_pull_request(repo_name, pr_number, head_sha, f"{title}\n\n{body}")


async def pull_request_review_handler(action: str, data, event, delivery, headers):
    if action != 'submitted':
        logger.info(f"Thread: {delivery}: Ignore action {action}")
    else:
        html_url = data['review']['html_url']
        pull_request_url = data['pull_request']['html_url']
        node_id = data['review']['node_id']
        body = data['review']['body']
        logger.info(f"Thread: {delivery}: Got a PR review {html_url} of {pull_request_url} {node_id} {body}")
        translator = translate.get_translator(settings.get_translator(),
                                              max_tokens=settings.TRANSLATION_MODEL.max_input_tokens)
        translated_body, has_translated_by_gpt, real_translated = await translator.translate(body)

        if real_translated:
            logger.info(f"Thread: {delivery}: Body:\n{translated_body}\n")
            try:
                await github.update_pullrequest_review(node_id,
                                                       translate.wrap_magic(translated_body, original_body=body))
                logger.info(f"Thread: {delivery}: Updated ok")
            except GithubGraphQLException as e:
                if e.is_forbidden():
                    logger.error(
                        f"Thread: {delivery}: Warning!!! Ignore update comment {node_id} failed, forbidden, {e.errors}")
                else:
                    logger.exception(f"Thread: {delivery}: Error!!! Update comment {node_id} failed, {e.errors}")
                    raise e


async def pull_request_review_comment_handler(action: str, data, event, delivery, headers):
    if action != 'created':
        logger.info(f"Thread: {delivery}: Ignore action {action}")
    else:
        html_url = data['comment']['html_url']
        pull_request_url = data['pull_request']['html_url']
        node_id = data['comment']['node_id']
        body = data['comment']['body']
        logger.info(
            f"Thread: {delivery}: PR review comments received {html_url} of {pull_request_url} {node_id} {body}")
        translator = translate.get_translator(settings.get_translator(),
                                              max_tokens=settings.TRANSLATION_MODEL.max_input_tokens)
        translated_body, has_translated_by_gpt, real_translated = await translator.translate(body)
        if real_translated:
            logger.info(f"Thread: {delivery}: Body:\n{translated_body}\n")
            try:
                await github.update_pullrequest_review_comment(node_id,
                                                               translate.wrap_magic(translated_body,
                                                                                    original_body=body))
                logger.info(f"Thread: {delivery}: Updated ok")
            except GithubGraphQLException as e:
                if e.is_forbidden():
                    logger.error(
                        f"Thread: {delivery}: Warning!!! Ignore update PR Review comment {node_id} failed, forbidden, {e.errors}")
                else:
                    logger.exception(
                        f"Thread: {delivery}: Error!!! Update PR Review comment {node_id} failed, {e.errors}")
                    raise e


async def commit_comment_handler(action: str, payload, event, delivery, headers):
    if action != 'created':
        logger.info(f"Thread: {delivery}: Ignore action {action}")
    else:
        html_url = payload['comment']['html_url']
        api_request_url = payload['comment']['url']
        repo_name = payload["repository"]["full_name"]
        comment_id = payload['comment']['id']
        body = payload['comment']['body']
        logger.info(f"Thread: {delivery}: commit comments received {html_url} of {api_request_url}"
                    f" {body}")
        translator = translate.get_translator(settings.get_translator(),
                                              max_tokens=settings.TRANSLATION_MODEL.max_input_tokens)
        translated_body, has_translated_by_gpt, real_translated = await translator.translate(body)
        if real_translated:
            logger.info(f"Thread: {delivery}: Body:\n{translated_body}\n")
            try:
                await github.update_commit_comment(repo_name, comment_id,
                                                   translate.wrap_magic(translated_body, original_body=body))
                logger.info(f"Thread: {delivery}: Updated ok")
            except Exception as e:
                logger.exception(
                    f"Thread: {delivery}: Error!!! Update Commit comment {html_url} failed, {e}")
                raise e


async def commit_handler(payload, event, delivery, headers):
    commit_id = payload['head_commit']['id']
    body = payload['head_commit']['message']
    repo_name = payload["repository"]["full_name"]
    commits = payload["commits"]
    # "https://github.com/ZLMediaKit/Github-AI-Assistant/commit/8547b7710226e80589e46570c546d8803b345647"
    url = payload['head_commit']['url']
    logger.info(f"Thread: {delivery}: Got a commit {commit_id}\n {url}\n {body}")
    translator = translate.get_translator(settings.get_translator(),
                                          max_tokens=settings.TRANSLATION_MODEL.max_input_tokens)
    translated_body, has_translated_by_gpt, real_translated = await translator.translate(body)
    if real_translated:
        logger.info(f"Thread: {delivery}: Body:\n{translated_body}\n")
        try:
            await github.create_commit_comment(repo_name, commit_id, translate.wrap_magic(translated_body))
            logger.info(f"Thread: {delivery}: Create Commit comment ok")
        except Exception as e:
            logger.exception(f"Thread: {delivery}: Error!!! Create Commit comment {url} failed, {e}")
            raise e
    else:
        logger.info(f"Thread: {delivery}: No need to translate")
    try:
        await handle_merged_push(repo_name, commits)
    except Exception as e:
        logger.exception(f"Thread: {delivery}: Error!!! Handle merged push failed, {e}")
    if not settings.REVIEW_MODEL.api_key:
        logger.info(f"Thread: {delivery}: No review model, skip")
        return
    await review.review_commits(repo_name, commits)


async def handle_github_request(data, event, delivery, headers):
    action = data['action'] if 'action' in data else None
    logger.info(f"Thread: {delivery}: Got an event {event} {action}, {headers}")

    if 'sender' in data and 'login' in data['sender']:
        sender = data['sender']['login']
        if github.IGNORE_LOGIN in sender:
            logger.info(f"Thread: {delivery}: Ignore sender {sender}")
            return
    if event == 'issues':
        await issues_handler(action, data, event, delivery, headers)
    elif event == 'issue_comment':
        await issue_comment_handler(action, data, event, delivery, headers)
    elif event == 'discussion':
        await discussion_handler(action, data, event, delivery, headers)
    elif event == 'discussion_comment':
        await discussion_comment_handler(action, data, event, delivery, headers)
    elif event == 'pull_request':
        await pull_request_handler(action, data, event, delivery, headers)
    elif event == 'pull_request_review':
        await pull_request_review_handler(action, data, event, delivery, headers)
    elif event == 'pull_request_review_comment':
        await pull_request_review_comment_handler(action, data, event, delivery, headers)
    elif event == "commit_comment":
        await commit_comment_handler(action, data, event, delivery, headers)
    elif event == "push":
        await commit_handler(data, event, delivery, headers)
    else:
        logger.info(f"Thread: {delivery}: Ignore event {event}")

    logger.info(f"Thread: {delivery}: Done")
