# -*- coding:utf-8 -*-
from sanic.log import logger

from apps import trans
from core import translate
from core.exception import GithubGraphQLException
from core.utils import github


async def handle_github_request(data, event, delivery, headers):
    action = data['action'] if 'action' in data else None
    logger.info(f"Thread: {delivery}: Got an event {event} {action}, {headers}")

    if 'sender' in data and 'login' in data['sender']:
        sender = data['sender']['login']
        if github.IGNORE_LOGIN in sender:
            logger.info(f"Thread: {delivery}: Ignore sender {sender}")
            return
    if event == 'issues':
        if action != 'opened':
            logger.info(f"Thread: {delivery}: Ignore action {action}")
        else:
            title = data['issue']['title']
            number = data['issue']['number']
            html_url = data['issue']['html_url']
            logger.info(f"Thread: {delivery}: Got an issue #{number} {html_url} {title}")
            result = await trans.trans_issues(html_url)
    elif event == 'issue_comment':
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
            body_trans, body_trans_by_gpt, real_translated = await translate.gpt_translate(body)
            if real_translated:
                logger.info(f"Thread: {delivery}: Body:\n{body_trans}\n")
                try:
                    await github.update_issue_comment(node_id, translate.wrap_magic(body_trans, original_body=body))
                    logger.info(f"Thread: {delivery}: Updated ok")
                except GithubGraphQLException as e:
                    if e.is_forbidden():
                        logger.error(
                            f"Thread: {delivery}: Warning!!! Ignore update comment {node_id} failed, forbidden, {e.errors}")
                    else:
                        raise e
    elif event == 'discussion':
        if action != 'created':
            logger.info(f"Thread: {delivery}: Ignore action {action}")
        else:
            html_url = data['discussion']['html_url']
            number = data['discussion']['number']
            title = data['discussion']['title']
            logger.info(f"Thread: {delivery}: Got a discussion #{number} {html_url} {title}")
            result = await trans.trans_discussion(html_url)
    elif event == 'discussion_comment':
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
            body_trans, body_trans_by_gpt, real_translated = await translate.gpt_translate(body)
            if real_translated:
                logger.info(f"Thread: {delivery}: Body:\n{body_trans}\n")
                try:
                    await github.update_discussion_comment(node_id,
                                                           translate.wrap_magic(body_trans, original_body=body))
                    logger.info(f"Thread: {delivery}: Updated ok")
                except GithubGraphQLException as e:
                    if e.is_forbidden():
                        logger.error(
                            f"Thread: {delivery}: Warning!!! Ignore update comment {node_id} failed, forbidden, {e.errors}")
                    else:
                        raise e
    elif event == 'pull_request':
        if action != 'opened':
            logger.info(f"Thread: {delivery}: Ignore action {action}")
        else:
            html_url = data['pull_request']['html_url']
            number = data['pull_request']['number']
            title = data['pull_request']['title']
            logger.info(f"Thread: {delivery}: Got a pull request #{number} {html_url} {title}")
            result = await trans.trans_pr(html_url)
    elif event == 'pull_request_review':
        if action != 'submitted':
            logger.info(f"Thread: {delivery}: Ignore action {action}")
        else:
            html_url = data['review']['html_url']
            pull_request_url = data['pull_request']['html_url']
            node_id = data['review']['node_id']
            body = data['review']['body']
            logger.info(f"Thread: {delivery}: Got a PR review {html_url} of {pull_request_url} {node_id} {body}")
            body_trans, body_trans_by_gpt, real_translated = await translate.gpt_translate(body)

            if real_translated:
                logger.info(f"Thread: {delivery}: Body:\n{body_trans}\n")
                try:
                    await github.update_pullrequest_review(node_id,
                                                           translate.wrap_magic(body_trans, original_body=body))
                    logger.info(f"Thread: {delivery}: Updated ok")
                except GithubGraphQLException as e:
                    if e.is_forbidden():
                        logger.error(
                            f"Thread: {delivery}: Warning!!! Ignore update comment {node_id} failed, forbidden, {e.errors}")
                    else:
                        raise e
    elif event == 'pull_request_review_comment':
        if action != 'created':
            logger.info(f"Thread: {delivery}: Ignore action {action}")
        else:
            html_url = data['comment']['html_url']
            pull_request_url = data['pull_request']['html_url']
            node_id = data['comment']['node_id']
            body = data['comment']['body']
            logger.info(
                f"Thread: {delivery}: PR review comments received {html_url} of {pull_request_url} {node_id} {body}")
            body_trans, body_trans_by_gpt, real_translated = await translate.gpt_translate(body)
            if real_translated:
                logger.info(f"Thread: {delivery}: Body:\n{body_trans}\n")
                try:
                    await github.update_pullrequest_review_comment(node_id,
                                                                   translate.wrap_magic(body_trans,
                                                                                        original_body=body))
                    logger.info(f"Thread: {delivery}: Updated ok")
                except GithubGraphQLException as e:
                    if e.is_forbidden():
                        print(
                            f"Thread: {delivery}: Warning!!! Ignore update PR Review comment {node_id} failed, forbidden, {e.errors}")
                    else:
                        raise e
    elif event == "commit_comment":
        if action != 'created':
            logger.info(f"Thread: {delivery}: Ignore action {action}")
        else:
            html_url = data['comment']['html_url']
            api_request_url = data['comment']['url']
            node_id = data['comment']['node_id']
            body = data['comment']['body']
            logger.info(f"Thread: {delivery}: commit comments received {html_url} of {api_request_url} {node_id}"
                        f" {body}")
            body_trans, body_trans_by_gpt, real_translated = await translate.gpt_translate(body)
            if real_translated:
                logger.info(f"Thread: {delivery}: Body:\n{body_trans}\n")
                try:
                    await github.update_commit_comment(node_id, translate.wrap_magic(body_trans, original_body=body))
                    logger.info(f"Thread: {delivery}: Updated ok")
                except GithubGraphQLException as e:
                    if e.is_forbidden():
                        print(
                            f"Thread: {delivery}: Warning!!! Ignore update PR Review comment {node_id} failed, forbidden, {e.errors}")
                    else:
                        raise e

    else:
        logger.info(f"Thread: {delivery}: Ignore event {event}")

    logger.info(f"Thread: {delivery}: Done")
