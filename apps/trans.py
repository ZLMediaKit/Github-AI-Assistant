# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#

__author__ = 'alex'

import hashlib
from typing import List

from core import translate, models, settings
from core.exception import GithubGraphQLException
from core.log import logger
from core.models import BaseDetail, Comment, Label
from core.utils import github
from core.utils.github import RepoDetail


async def update_issue_comment(comment: Comment, translated_body: str, original_body: str):
    try:
        await github.update_issue_comment(comment.id,
                                          translate.wrap_magic(translated_body, original_body=original_body))
        logger.info("Updated ok")
    except GithubGraphQLException as e:
        if e.is_forbidden():
            logger.error(f"Warning!!! Ignore update comment {comment.id} failed, forbidden, {e.errors}")
        else:
            logger.exception(f"update_issue_comment failed, {e}")
            raise e


async def trans_comments(comments: List[Comment]) -> bool:
    has_translated_by_gpt = False
    for index, detail in enumerate(comments):
        logger.info(f"===============Comment(#{index + 1})===============\n{detail.get_detail_text()}")
        if translate.TRANS_MAGIC in detail.body:
            has_translated_by_gpt = True
            logger.info("Already translated, skip")
            continue
        logger.info("Translating...")
        translator = translate.get_translator(settings.get_translator(),
                                              max_tokens=settings.TRANSLATION_MODEL.max_input_tokens)
        translated_body, has_translated_by_gpt, real_translated = await translator.translate(detail.body)
        if real_translated:
            logger.info(f"New Body:\n{translated_body}\n")
            await update_issue_comment(detail, translated_body, detail.body)
    return has_translated_by_gpt


async def update_detail(detail_type: str, detail_id: str, translated_title: str, translated_body: str,
                        original_title: str, original_body: str):
    try:
        if detail_type == models.DETAIL_TYPE_ISSUE:
            await github.update_issue(detail_id, translated_title,
                                      translate.wrap_magic(translated_body,
                                                           original_body=original_body),
                                      original_title=original_title)
        elif detail_type == models.DETAIL_TYPE_DISCUSSION:
            await github.update_discussion(detail_id, translated_title,
                                           translate.wrap_magic(translated_body, original_body=original_body),
                                           original_title=original_title)
        elif detail_type == models.DETAIL_TYPE_PR:
            await github.update_pullrequest(detail_id, translated_title,
                                            translate.wrap_magic(translated_body,
                                                                 translate.TRANS_DELIMITER_PR,
                                                                 original_body=original_body),
                                            original_title=original_title)
        logger.info("Updated ok")
    except GithubGraphQLException as e:
        if e.is_forbidden():
            logger.warning(f"Warning!!! Ignore update [{detail_type}] {detail_id} failed, forbidden, {e.errors}")
        else:
            logger.exception(f"update_detail failed, {e}")
            raise e


async def trans_comments_by_type(detail: BaseDetail) -> bool:
    if detail.model_type_text == models.DETAIL_TYPE_ISSUE:
        return await trans_comments(detail.comments)
    elif detail.model_type_text == models.DETAIL_TYPE_DISCUSSION:
        return await trans_discussion_comments(detail.comments)
    elif detail.model_type_text == models.DETAIL_TYPE_PR:
        return await trans_pr_comments(detail.comments, detail.reviews)


async def trans_detail(detail: BaseDetail, repo_detail: RepoDetail):
    has_gpt_label = False
    has_en_native_label = False
    for label in detail.labels:
        if label.name == github.LABEL_TRANS.name:
            has_gpt_label = True
        if label.name == github.LABEL_ENGLISH_NATIVE.name:
            has_en_native_label = True
    logger.info("")
    logger.info(detail.get_detail_text())
    issue_changed = False
    issue_has_translated_by_gpt = False
    translated_title = detail.title
    translated_body = detail.body
    if translate.TRANS_MAGIC in detail.body:
        issue_has_translated_by_gpt = True
        logger.info("Body is already translated, skip")
    elif translate.already_english(detail.body):
        logger.info("Body is already english, skip")
    else:
        logger.info("Translating...")
        if translate.already_english(detail.title):
            logger.info("Title is already english, skip")
        else:
            translator = translate.get_translator(settings.get_translator(),
                                                  max_tokens=settings.TRANSLATION_MODEL.max_input_tokens)
            translated_title, has_translated_by_gpt, real_translated = await translator.translate(detail.title)
            if real_translated:
                issue_changed = True
                logger.info(f"New Title is: {translated_title}")
        translator = translate.get_translator(settings.get_translator(),
                                              max_tokens=settings.TRANSLATION_MODEL.max_input_tokens)
        translated_body, has_translated_by_gpt, real_translated = await translator.translate(detail.body)
        if has_translated_by_gpt:
            issue_has_translated_by_gpt = True
        if real_translated:
            issue_changed = True
            logger.info(f"New Body:\n{translated_body}\n")
    if not issue_changed:
        logger.info("Nothing changed, skip")
    else:
        await update_detail(detail.model_type_text, detail.id, translated_title, translated_body,
                            detail.title, detail.body)
    comment_has_translated_by_gpt = await trans_comments_by_type(detail)
    translated_by_gpt = comment_has_translated_by_gpt or issue_has_translated_by_gpt
    if translated_by_gpt or has_gpt_label:
        logger.info("Label is already set, skip")
    else:
        await add_label(detail.id, repo_detail, github.LABEL_TRANS)
        has_gpt_label = True

    if not translated_by_gpt and not has_gpt_label and not has_en_native_label:
        await add_label(detail.id, repo_detail, github.LABEL_ENGLISH_NATIVE)
    logger.info("Translation completed")


async def add_label(detail_id: str, repo_detail: RepoDetail, label: Label):
    logger.info(f"Add label {label.name} to {detail_id}")
    label_id = await github.query_label_id(repo_detail.owner, repo_detail.name, label.name)
    if label_id is None:
        try:
            label_id = await github.create_label_with_repo_details(repo_detail.owner, repo_detail.name, label)
        except Exception as e:
            logger.exception(f"Create label failed, {e}")
    if label_id:
        logger.info(f"Query LABEL_TRANS_NAME={label.name}, got LABEL_ID={label_id}")
        await github.add_label(detail_id, label_id)
        logger.info(f"Add label successful, {label_id}({label.name})")


async def trans_issues(issues_url):
    """
    :param issues_url:
    :return:
    """
    logger.info(f"run with issues: {issues_url}, use ai model: {settings.TRANSLATION_MODEL.model_name}")
    repo_detail = github.parse_issue_url(issues_url)
    try:
        issues_detail = await github.query_issue(repo_detail)
    except Exception as e:
        logger.exception(f"query_issue failed, {e}")
        return False
    await trans_detail(issues_detail, repo_detail)


async def trans_discussion_comments(comments: List[Comment]) -> bool:
    has_translated_by_gpt = False
    for index, detail in enumerate(comments):
        c_id = detail["id"]
        c_author = detail["author"]["login"]
        c_replies = detail["replies"]['totalCount']
        c_url = detail["url"]
        c_body = detail["body"]
        logger.info("")
        log_list = [f"===============Comment(#{index + 1})===============",
                    f"ID: {c_id}",
                    f"Author: {c_author}",
                    f"Replies: {c_replies}",
                    f"URL: {c_url}",
                    f"Body:\n{c_body}\n"]
        logger.info("\n".join(log_list))
        if translate.TRANS_MAGIC in c_body:
            has_translated_by_gpt = True
            logger.info("Already translated, skip")
        elif translate.already_english(c_body):
            logger.info("Body is already english, skip")
        else:
            logger.info("Translating...")
            translator = translate.get_translator(settings.get_translator(),
                                                  max_tokens=settings.TRANSLATION_MODEL.max_input_tokens)
            translated_body, has_translated_by_gpt, real_translated = await translator.translate(c_body)
            if real_translated:
                logger.info(f"New Body:\n{translated_body}\n")
                try:
                    await github.update_discussion_comment(c_id,
                                                           translate.wrap_magic(translated_body, original_body=c_body))
                    logger.info("Updated ok")
                except GithubGraphQLException as e:
                    if e.is_forbidden():
                        logger.error(f"Warning!!! Ignore update comment {c_id} failed, forbidden, {e.errors}")
                    else:
                        logger.exception(f"update_discussion_comment failed, {e}")
                        raise e
        for position, reply_obj in enumerate(detail["replies"]["nodes"]):
            reply_id = reply_obj["id"]
            reply_author = reply_obj["author"]["login"]
            reply_url = reply_obj["url"]
            reply_body = reply_obj["body"]
            logger.info(f"---------------Reply(#{position + 1})---------------")
            logger.info(f"ID: {reply_id}")
            logger.info(f"Author: {reply_author}")
            logger.info(f"URL: {reply_url}")
            logger.info(f"Body:\n{reply_body}\n")

            if translate.TRANS_MAGIC in reply_body:
                has_translated_by_gpt = True
                logger.info("Already translated, skip")
            elif translate.already_english(reply_body):
                logger.info("Body is already english, skip")
            else:
                logger.info("Translating...")
                translator = translate.get_translator(settings.get_translator(),
                                                      max_tokens=settings.TRANSLATION_MODEL.max_input_tokens)
                reply_body_trans, has_translated_by_gpt, real_translated = translator.translate(reply_body)
                if real_translated:
                    logger.info(f"New Body:\n{reply_body_trans}\n")
                    await github.update_discussion_comment(reply_id,
                                                           translate.wrap_magic(reply_body_trans,
                                                                                original_body=reply_body))
                    logger.info("Updated ok")
    return has_translated_by_gpt


async def trans_discussion(discussion_url):
    """
    Translate discussion
    :param discussion_url:
    :return:
    """
    logger.info(f"run with discussion: {discussion_url}, use ai model: {settings.TRANSLATION_MODEL.model_name}")
    repo_detail = github.parse_discussion_url(discussion_url)
    try:
        discussion_detail = await github.query_discussion(repo_detail)
    except Exception as e:
        logger.exception(f"query_issue failed, {e}")
        return False
    await trans_detail(discussion_detail, repo_detail)


async def trans_pr_comments(comments, reviews):
    has_translated_by_gpt = False
    for index, detail in enumerate(comments):
        c_id = detail["id"]
        c_url = detail["url"]
        c_body = detail["body"]
        logger.info("")
        logger.info(f"===============Comment(#{index + 1})===============")
        logger.info(f"ID: {c_id}")
        logger.info(f"URL: {c_url}")
        logger.info(f"Body:\n{c_body}\n")

        if translate.TRANS_MAGIC in c_body:
            has_translated_by_gpt = True
            logger.info("Already translated, skip")
        elif translate.already_english(c_body):
            logger.info("Body is already english, skip")
        else:
            logger.info("Translating...")
            translator = translate.get_translator(settings.get_translator(),
                                                  max_tokens=settings.TRANSLATION_MODEL.max_input_tokens)
            c_body_trans, has_translated_by_gpt, real_translated = await translator.translate(c_body)
            if real_translated:
                logger.info(f"New Body:\n{c_body_trans}\n")
                try:
                    await github.update_issue_comment(c_id,
                                                      translate.wrap_magic(c_body_trans, original_body=c_body))
                    logger.info("Updated ok")
                except GithubGraphQLException as e:
                    if e.is_forbidden():
                        logger.error(f"Warning!!! Ignore update comment {c_id} failed, forbidden, {e.errors}")
                    else:
                        logger.exception(f"update_issue_comment failed, {e}")
                        raise e
        for position, review_obj in enumerate(reviews):
            c_id = review_obj["id"]
            c_comments = review_obj["comments"]['totalCount']
            c_url = review_obj["url"]
            c_body = review_obj["body"]
            logger.info(f"===============Review(#{index + 1})===============")
            logger.info(f"ID: {c_id}")
            logger.info(f"Comments: {c_comments}")
            logger.info(f"URL: {c_url}")
            logger.info(f"Body:\n{c_body}\n")

            if translate.TRANS_MAGIC in c_body:
                has_translated_by_gpt = True
                logger.info("Already translated, skip")
            elif translate.already_english(c_body):
                logger.info("Body is already english, skip")
            else:
                logger.info("Translating...")
                translator = translate.get_translator(settings.get_translator(),
                                                      max_tokens=settings.TRANSLATION_MODEL.max_input_tokens)
                c_body_trans, has_translated_by_gpt, real_translated = await translator.translate(c_body)
                if real_translated:
                    logger.info(f"New Body:\n{c_body_trans}\n")
                    await github.update_pullrequest_review(c_id,
                                                           translate.wrap_magic(c_body_trans, original_body=c_body))
                    logger.info("Updated ok")

            for reply_position, review_reply_obj in enumerate(review_obj["comments"]["nodes"]):
                reply_id = review_reply_obj["id"]
                reply_url = review_reply_obj["url"]
                reply_body = review_reply_obj["body"]
                logger.info(f"---------------ReviewComment(#{reply_position + 1})---------------")
                logger.info(f"ID: {reply_id}")
                logger.info(f"URL: {reply_url}")
                logger.info(f"Body:\n{reply_body}\n")

                if translate.TRANS_MAGIC in reply_body:
                    has_translated_by_gpt = True
                    print("Already translated, skip")
                elif translate.already_english(reply_body):
                    print("Body is already english, skip")
                else:
                    logger.info("Translating...")
                    translator = translate.get_translator(settings.get_translator(),
                                                          max_tokens=settings.TRANSLATION_MODEL.max_input_tokens)
                    reply_body_trans, has_translated_by_gpt, real_translated = await translator.translate(reply_body)
                    if real_translated:
                        logger.info(f"New Body:\n{reply_body_trans}\n")
                        await github.update_pullrequest_review_comment(reply_id,
                                                                       translate.wrap_magic(reply_body_trans,
                                                                                            original_body=reply_body))
                        logger.info("Updated ok")
    return has_translated_by_gpt


async def trans_pr(pr_url):
    """
    Translate pull request
    :param pr_url:
    :return:
    """
    logger.info(f"run with pull request: {pr_url}, use ai model: {settings.TRANSLATION_MODEL.model_name}")
    repo_detail = github.parse_pullrequest_url(pr_url)
    try:
        pr_detail = await github.query_pullrequest_all_in_one(repo_detail)
    except Exception as e:
        logger.exception(f"query_issue failed, {e}")
        return False
    await trans_detail(pr_detail, repo_detail)


async def batch_trans(input_url, query_filter, query_limit):
    if 'is:' not in query_filter:
        query_filter = f"is:{query_filter}"
    logs = []
    logs.append(f"repository: {input_url}")
    logs.append(f"query_filter: {query_filter}")
    logs.append(f"query_limit: {query_limit}")
    logger.info(f"run with {', '.join(logs)}, use ai model: {settings.TRANSLATION_MODEL.model_name}")

    if query_limit <= 0 or query_limit > 100:
        logger.error("query_limit should be in [1, 100]")
        return

    repository = github.parse_repository_url(input_url)
    query_results = await github.search_issues(
        repository["owner"],
        repository["name"],
        query_filter,
        "sort:comments-desc",
        [f"-label:{github.LABEL_TRANS.name}", f"-label:{github.LABEL_ENGLISH_NATIVE.name}"],
        query_limit,
    )

    comments = 0
    for issue in query_results:
        comments += issue["comments"]["totalCount"]
    logger.info(f"Start to translate {len(query_results)} objects, {comments} comments.")

    for index, issue in enumerate(query_results):
        logger.info("\n\n\n\n\n\n")
        logger.info(f"===============Object(#{index + 1})===============")
        logger.info(f"ID: {issue['id']}")
        logger.info(f"Title: {issue['title']}")
        logger.info(f"URL: {issue['url']}")
        if 'issue' in query_filter:
            await trans_issues(issue["url"])
        elif 'pr' in query_filter or 'pullrequest' in query_filter:
            await trans_pr(issue["url"])
        elif 'discussion' in query_filter:
            await trans_discussion(issue["url"])
        else:
            logger.error("query_filter should be in [issue, pr, discussion]")
            return


async def translate_text(text):
    logger.info(f"Translating text: {text}")
    translator = translate.get_translator(settings.get_translator(),
                                          max_tokens=settings.TRANSLATION_MODEL.max_input_tokens)
    translated_body, _, _ = await translator.translate(text)
    logger.info(f"Translated text: {translated_body}")
    return translated_body


async def process_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    comments = list(translate.extract_comments(content))
    non_english_comments = []
    replacements = []

    for comment in comments:
        if not translate.already_english(comment.group(2)) and not translate.is_already_translated(comment.group()):
            non_english_comments.append(comment)
    if not non_english_comments:
        logger.info(f"There is no comment to translate in {file_path}")
        return False
    for i in range(0, len(non_english_comments), translate.BATCH_SIZE):
        batch = non_english_comments[i:i + translate.BATCH_SIZE]
        batch_text = "\n[|||]\n".join(comment.group(2) for comment in batch)
        translation = await translate_text(batch_text)
        if translation:
            translations = translation.split("\n[|||]\n")
            for comment, trans in zip(batch, translations):
                indentation, original = comment.groups()
                comment_hash = hashlib.md5(original.encode()).hexdigest()[:8]
                trans = trans.replace("/**\n", "").replace("*/", "")
                replacement = translate.format_translated_comment(comment.group(), trans, indentation, comment_hash)
                replacements.append((comment.start(), comment.end(), replacement))

    # 按照逆序排列替换，以保持正确的索引
    for start, end, replacement in sorted(replacements, reverse=True):
        content = content[:start] + replacement + content[end:]

    # 验证修改后的内容
    validation_result, error_message = translate.validate_code(content)
    if validation_result:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        return True
    else:
        logger.warning(f"WARN: Code validation failed for {file_path}. Changes not saved.")
        logger.warning(f"In file {file_path}, validation error: {error_message}")
        return False


async def trans_sourcecode_comments(project_path):
    cpp_files = translate.find_cpp_files(project_path)
    for file in cpp_files:
        logger.info(f"Processing file: {file}")
        try:
            result = process_file(file)
            if result:
                logger.info(f"Successfully processed file: {file}")
            else:
                logger.warning(f"Failed to process file: {file}")
        except Exception as e:
            logger.exception(f"While processing {file}, error: {e}")
