# -*- coding:utf-8 -*-
from sanic.log import logger

from apps import trans
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
            logger.info(f"Already translated, skip")
            return has_translated_by_gpt
        translator = translate.get_translator(settings.get_translator(), max_tokens=settings.get_max_tokens())
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
            logger.info(f"Already translated, skip")
            return has_translated_by_gpt
        translator = translate.get_translator(settings.get_translator(), max_tokens=settings.get_max_tokens())
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


async def pull_request_handler(action: str, data, event, delivery, headers):
    if action != 'opened':
        logger.info(f"Thread: {delivery}: Ignore action {action}")
    else:
        html_url = data['pull_request']['html_url']
        number = data['pull_request']['number']
        title = data['pull_request']['title']
        logger.info(f"Thread: {delivery}: Got a pull request #{number} {html_url} {title}")
        result = await trans.trans_pr(html_url)


async def pull_request_review_handler(action: str, data, event, delivery, headers):
    if action != 'submitted':
        logger.info(f"Thread: {delivery}: Ignore action {action}")
    else:
        html_url = data['review']['html_url']
        pull_request_url = data['pull_request']['html_url']
        node_id = data['review']['node_id']
        body = data['review']['body']
        logger.info(f"Thread: {delivery}: Got a PR review {html_url} of {pull_request_url} {node_id} {body}")
        translator = translate.get_translator(settings.get_translator(), max_tokens=settings.get_max_tokens())
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
        translator = translate.get_translator(settings.get_translator(), max_tokens=settings.get_max_tokens())
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


async def commit_comment_handler(action: str, data, event, delivery, headers):
    if action != 'created':
        logger.info(f"Thread: {delivery}: Ignore action {action}")
    else:
        html_url = data['comment']['html_url']
        api_request_url = data['comment']['url']
        node_id = data['comment']['node_id']
        body = data['comment']['body']
        logger.info(f"Thread: {delivery}: commit comments received {html_url} of {api_request_url} {node_id}"
                    f" {body}")
        translator = translate.get_translator(settings.get_translator(), max_tokens=settings.get_max_tokens())
        translated_body, has_translated_by_gpt, real_translated = await translator.translate(body)
        if real_translated:
            logger.info(f"Thread: {delivery}: Body:\n{translated_body}\n")
            try:
                await github.update_commit_comment(node_id, translate.wrap_magic(translated_body, original_body=body))
                logger.info(f"Thread: {delivery}: Updated ok")
            except GithubGraphQLException as e:
                if e.is_forbidden():
                    logger.error(
                        f"Thread: {delivery}: Warning!!! Ignore update PR Review comment {node_id} failed, forbidden, {e.errors}")
                else:
                    logger.exception(
                        f"Thread: {delivery}: Error!!! Update PR Review comment {node_id} failed, {e.errors}")
                    raise e


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
    # elif event == "commit_comment":
    #     await commit_comment_handler(action, data, event, delivery, headers)
    else:
        logger.info(f"Thread: {delivery}: Ignore event {event}")

    logger.info(f"Thread: {delivery}: Done")