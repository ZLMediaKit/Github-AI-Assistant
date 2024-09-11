# -*- coding:utf-8 -*-

#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#

from sanic.log import logger

from apps import trans, review
from core import translate, settings
from core.exception import GithubGraphQLException
from core.utils import github


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
    if action not in ["opened", "synchronize"]:
        logger.info(f"Thread: {delivery}: Ignore action {action}")
        return
    else:
        html_url = payload['pull_request']['html_url']
        number = payload['pull_request']['number']
        title = payload['pull_request']['title']
        logger.info(f"Thread: {delivery}: Got a pull request #{number} {html_url} {title}")
        result = await trans.trans_pr(html_url)
    repo_name = payload["repository"]["full_name"]
    pr_number = payload["number"]
    head_sha = payload["pull_request"]["head"]["sha"]
    if not settings.REVIEW_MODEL.api_key:
        logger.info(f"Thread: {delivery}: No review model, skip")
        return
    await review.review_pull_request(repo_name, pr_number, head_sha, title)


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
