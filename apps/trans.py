# -*- coding:utf-8 -*-
__author__ = 'alex'

from core.exception import GithubGraphQLException
from core.log import logger
from core import settings
from core import trans_helper
from core import github_helper


def trans_comments(comments):
    has_translated_by_gpt = False
    for index, detail in enumerate(comments):
        c_id = detail["id"]
        c_author = detail["author"]["login"]
        c_url = detail["url"]
        c_body = detail["body"]
        logger.info(f"===============Comment(#{index + 1})===============")
        logger.info(f"ID: {c_id}")
        logger.info(f"Author: {c_author}")
        logger.info(f"URL: {c_url}")
        logger.info(f"Body:\n{c_body}\n")
        if trans_helper.TRANS_MAGIC in c_body:
            has_translated_by_gpt = True
            logger.info(f"Already translated, skip")
            return has_translated_by_gpt
        logger.info(f"Translating...")
        c_body_trans, has_translated_by_gpt, real_translated = trans_helper.gpt_translate(c_body)
        if real_translated:
            logger.info(f"New Body:\n{c_body_trans}\n")
            try:
                github_helper.update_issue_comment(c_id, trans_helper.wrap_magic(c_body_trans, original_body=c_body))
                logger.info(f"Updated ok")
            except GithubGraphQLException as e:
                if e.is_forbidden():
                    logger.error(f"Warning!!! Ignore update comment {c_id} failed, forbidden, {e.errors}")
                else:
                    raise e
    return has_translated_by_gpt


def trans_detail(labels, detail_type, detail_id, detail_url, title, body, comment_has_translated_by_gpt, repo_detail):
    has_gpt_label = False
    has_en_native_label = False
    labels4print = []
    for label in labels:
        if label["name"] == github_helper.LABEL_TRANS_NAME:
            has_gpt_label = True
        if label["name"] == github_helper.LABEL_ENGLISH_NATIVE:
            has_en_native_label = True
        labels4print.append(f"{label['id']}({label['name']})")
    logger.info("")
    if detail_type == "issues":
        logger.info(f"===============ISSUE===============")
    elif detail_type == "discussion":
        logger.info(f"===============DISCUSSION===============")
    elif detail_type == "pull_request":
        logger.info(f"===============PULL_REQUEST===============")
    logger.info(f"ID: {detail_id}")
    logger.info(f"Url: {detail_url}")
    logger.info(f"Title: {title}")
    logger.info(f"Labels: {', '.join(labels4print)}")
    logger.info(f"Body:\n{body}\n")

    issue_changed = False
    issue_has_translated_by_gpt = False
    title_trans = title
    body_trans = body
    if trans_helper.TRANS_MAGIC in body:
        issue_has_translated_by_gpt = True
        logger.info(f"Body is already translated, skip")
    elif trans_helper.already_english(body):
        logger.info(f"Body is already english, skip")
    else:
        logger.info(f"Translating...")
        if trans_helper.already_english(title):
            logger.info(f"Title is already english, skip")
        else:
            title_trans, has_translated_by_gpt, real_translated = trans_helper.gpt_translate(title)
            if real_translated:
                issue_changed = True
                logger.info(f"New Title is: {title_trans}")
        body_trans, has_translated_by_gpt, real_translated = trans_helper.gpt_translate(body)
        if has_translated_by_gpt:
            issue_has_translated_by_gpt = True
        if real_translated:
            issue_changed = True
            logger.info(f"New Body:\n{body_trans}\n")
    if not issue_changed:
        logger.info(f"Nothing changed, skip")
    else:
        try:
            if detail_type == "issues":
                github_helper.update_issue(detail_id, title_trans,
                                           trans_helper.wrap_magic(body_trans, original_body=body),
                                           original_title=title)
            elif detail_type == "discussion":
                github_helper.update_discussion(detail_id, title_trans,
                                                trans_helper.wrap_magic(body_trans, original_body=body),
                                                original_title=title)
            elif detail_type == "pull_request":
                github_helper.update_pullrequest(detail_id, title_trans,
                                                 trans_helper.wrap_magic(body_trans, trans_helper.TRANS_DELIMETER_PR,
                                                                         original_body=body),
                                                 original_title=title)
            logger.info(f"Updated ok")
        except GithubGraphQLException as e:
            if e.is_forbidden():
                logger.info(f"Warning!!! Ignore update issue {detail_id} failed, forbidden, {e.errors}")
            else:
                raise e

    any_by_gpt = comment_has_translated_by_gpt or issue_has_translated_by_gpt
    if not any_by_gpt or has_gpt_label:
        logger.info(f"Label is already set, skip")
    else:
        logger.info(f"Add label {github_helper.LABEL_TRANS_NAME}")
        label_id = github_helper.query_label_id(repo_detail["owner"], repo_detail["name"],
                                                github_helper.LABEL_TRANS_NAME)
        logger.info(f"Query LABEL_TRANS_NAME={github_helper.LABEL_TRANS_NAME}, got LABEL_ID={label_id}")

        github_helper.add_label(detail_id, label_id)
        logger.info(f"Add label ok, {label_id}({github_helper.LABEL_TRANS_NAME})")

    if not any_by_gpt and not has_gpt_label and not has_en_native_label:
        logger.info(f"Add label {github_helper.LABEL_ENGLISH_NATIVE}")
        label_id = github_helper.query_label_id(repo_detail["owner"], repo_detail["name"],
                                                github_helper.LABEL_ENGLISH_NATIVE)
        logger.info(f"Query LABEL_ENGLISH_NATIVE={github_helper.LABEL_ENGLISH_NATIVE}, got LABEL_ID={label_id}")
        github_helper.add_label(detail_id, label_id)
        logger.info(f"Add label ok, {label_id}({github_helper.LABEL_ENGLISH_NATIVE})")

    logger.info("Translation completed")


def trans_issues(issues_url):
    """
    :param issues_url:
    :return:
    """
    logger.info(f"run with issues: {issues_url}, use ai model: {trans_helper.get_ai_model()}")

    repo_detail = github_helper.parse_issue_url(issues_url)
    try:
        issues_detail = github_helper.query_issue(repo_detail["owner"], repo_detail["name"], repo_detail["number"])
    except Exception as e:
        logger.exception(f"query_issue failed, {e}")
        return False

    comments = issues_detail['comments']
    comment_has_translated_by_gpt = trans_comments(comments)
    issues_id = issues_detail["id"]
    title = issues_detail["title"]
    body = issues_detail["body"]

    trans_detail(issues_detail["labels"], "issues",
                 issues_id, issues_url, title, body, comment_has_translated_by_gpt, repo_detail)


def trans_discussion_comments(comments):
    has_translated_by_gpt = False
    for index, detail in enumerate(comments):
        c_id = detail["id"]
        c_author = detail["author"]["login"]
        c_replies = detail["replies"]['totalCount']
        c_url = detail["url"]
        c_body = detail["body"]
        logger.info("")
        logger.info(f"===============Comment(#{index + 1})===============")
        logger.info(f"ID: {c_id}")
        logger.info(f"Author: {c_author}")
        logger.info(f"Replies: {c_replies}")
        logger.info(f"URL: {c_url}")
        logger.info(f"Body:\n{c_body}\n")

        if trans_helper.TRANS_MAGIC in c_body:
            has_translated_by_gpt = True
            logger.info(f"Already translated, skip")
        elif trans_helper.already_english(c_body):
            logger.info(f"Body is already english, skip")
        else:
            logger.info(f"Translating...")
            c_body_trans, has_translated_by_gpt, real_translated = trans_helper.gpt_translate(c_body)
            if real_translated:
                logger.info(f"New Body:\n{c_body_trans}\n")
                try:
                    github_helper.update_discussion_comment(c_id,
                                                            trans_helper.wrap_magic(c_body_trans, original_body=c_body))
                    logger.info(f"Updated ok")
                except GithubGraphQLException as e:
                    if e.is_forbidden():
                        logger.error(f"Warning!!! Ignore update comment {c_id} failed, forbidden, {e.errors}")
                    else:
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

            if trans_helper.TRANS_MAGIC in reply_body:
                has_translated_by_gpt = True
                logger.info(f"Already translated, skip")
            elif trans_helper.already_english(reply_body):
                logger.info(f"Body is already english, skip")
            else:
                logger.info(f"Translating...")
                reply_body_trans, has_translated_by_gpt, real_translated = trans_helper.gpt_translate(reply_body)
                if real_translated:
                    logger.info(f"New Body:\n{reply_body_trans}\n")
                    github_helper.update_discussion_comment(reply_id,
                                                            trans_helper.wrap_magic(reply_body_trans,
                                                                                    original_body=reply_body))
                    logger.info(f"Updated ok")
    return has_translated_by_gpt


def trans_discussion(discussion_url):
    """
    Translate discussion
    :param discussion_url:
    :return:
    """
    logger.info(f"run with discussion: {discussion_url}, use ai model: {trans_helper.get_ai_model()}")
    repo_detail = github_helper.parse_discussion_url(discussion_url)
    try:
        discussion_detail = github_helper.query_discussion(repo_detail["owner"], repo_detail["name"],
                                                           repo_detail["number"])
    except Exception as e:
        logger.exception(f"query_issue failed, {e}")
        return False
    comments = discussion_detail['comments']
    comment_has_translated_by_gpt = trans_discussion_comments(comments)
    discussion_id = discussion_detail["id"]
    title = discussion_detail["title"]
    body = discussion_detail["body"]
    trans_detail(discussion_detail["labels"], "discussion",
                 discussion_id, discussion_url, title, body, comment_has_translated_by_gpt, repo_detail)


def trans_pr_comments(comments, reviews):
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

        if trans_helper.TRANS_MAGIC in c_body:
            has_translated_by_gpt = True
            logger.info(f"Already translated, skip")
        elif trans_helper.already_english(c_body):
            logger.info(f"Body is already english, skip")
        else:
            logger.info(f"Translating...")
            c_body_trans, has_translated_by_gpt, real_translated = trans_helper.gpt_translate(c_body)
            if real_translated:
                logger.info(f"New Body:\n{c_body_trans}\n")
                try:
                    github_helper.update_issue_comment(c_id,
                                                       trans_helper.wrap_magic(c_body_trans, original_body=c_body))
                    logger.info(f"Updated ok")
                except GithubGraphQLException as e:
                    if e.is_forbidden():
                        logger.error(f"Warning!!! Ignore update comment {c_id} failed, forbidden, {e.errors}")
                    else:
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

            if trans_helper.TRANS_MAGIC in c_body:
                has_translated_by_gpt = True
                logger.info(f"Already translated, skip")
            elif trans_helper.already_english(c_body):
                logger.info(f"Body is already english, skip")
            else:
                logger.info(f"Translating...")
                c_body_trans, has_translated_by_gpt, real_translated = trans_helper.gpt_translate(c_body)
                if real_translated:
                    logger.info(f"New Body:\n{c_body_trans}\n")
                    github_helper.update_pullrequest_review(c_id,
                                                            trans_helper.wrap_magic(c_body_trans, original_body=c_body))
                    logger.info(f"Updated ok")

            for reply_position, review_reply_obj in enumerate(review_obj["comments"]["nodes"]):
                reply_id = review_reply_obj["id"]
                reply_url = review_reply_obj["url"]
                reply_body = review_reply_obj["body"]
                logger.info(f"---------------ReviewComment(#{reply_position + 1})---------------")
                logger.info(f"ID: {reply_id}")
                logger.info(f"URL: {reply_url}")
                logger.info(f"Body:\n{reply_body}\n")

                if trans_helper.TRANS_MAGIC in reply_body:
                    has_translated_by_gpt = True
                    print(f"Already translated, skip")
                elif trans_helper.already_english(reply_body):
                    print(f"Body is already english, skip")
                else:
                    logger.info(f"Translating...")
                    reply_body_trans, has_translated_by_gpt, real_translated = trans_helper.gpt_translate(reply_body)
                    if real_translated:
                        logger.info(f"New Body:\n{reply_body_trans}\n")
                        github_helper.update_pullrequest_review_comment(reply_id,
                                                                        trans_helper.wrap_magic(reply_body_trans,
                                                                                                original_body=reply_body))
                        logger.info(f"Updated ok")
    return has_translated_by_gpt


def trans_pr(pr_url):
    """
    Translate pull request
    :param pr_url:
    :return:
    """
    logger.info(f"run with pull request: {pr_url}, use ai model: {trans_helper.get_ai_model()}")
    repo_detail = github_helper.parse_pullrequest_url(pr_url)
    try:
        pr_detail = github_helper.query_pullrequest_all_in_one(repo_detail["owner"], repo_detail["name"],
                                                               repo_detail["number"])
    except Exception as e:
        logger.exception(f"query_issue failed, {e}")
        return False
    comments = pr_detail['comments']
    reviews = pr_detail['reviews']
    comment_has_translated_by_gpt = trans_pr_comments(comments, reviews)
    pr_id = pr_detail["id"]
    title = pr_detail["title"]
    body = pr_detail["body"]
    trans_detail(pr_detail["labels"], "pull_request",
                 pr_id, pr_url, title, body, comment_has_translated_by_gpt, repo_detail)


def batch_trans(input_url, query_filter, query_limit):
    if 'is:' not in query_filter:
        query_filter = f"is:{query_filter}"
    logs = []
    logs.append(f"repository: {input_url}")
    logs.append(f"query_filter: {query_filter}")
    logs.append(f"query_limit: {query_limit}")
    logger.info(f"run with {', '.join(logs)}, use ai model: {trans_helper.get_ai_model()}")

    if query_limit <= 0 or query_limit > 100:
        logger.error("query_limit should be in [1, 100]")
        return

    repository = github_helper.parse_repository_url(input_url)
    query_results = github_helper.search_issues(
        repository["owner"],
        repository["name"],
        query_filter,
        "sort:comments-desc",
        [f"-label:{github_helper.LABEL_TRANS_NAME}", f"-label:{github_helper.LABEL_ENGLISH_NATIVE}"],
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
            trans_issues(issue["url"])
        elif 'pr' in query_filter or 'pullrequest' in query_filter:
            trans_pr(issue["url"])
        elif 'discussion' in query_filter:
            trans_discussion(issue["url"])
        else:
            logger.error("query_filter should be in [issue, pr, discussion]")
            return


def handle_github_request(data, event, delivery, headers):
    action = data['action'] if 'action' in data else None
    logger.info(f"Thread: {delivery}: Got an event {event} {action}, {headers}")

    if 'sender' in data and 'login' in data['sender']:
        sender = data['sender']['login']
        if github_helper.IGNORE_LOGIN in sender:
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
            result = trans_issues(html_url)
    elif event == 'issue_comment':
        if action != 'created':
            logger.info(f"Thread: {delivery}: Ignore action {action}")
        else:
            html_url = data['comment']['html_url']
            issue_url = data['issue']['html_url']
            node_id = data['comment']['node_id']
            body = data['comment']['body']
            logger.info(f"Thread: {delivery}: Got a comment {html_url} of {issue_url} {node_id} {body}")
            if trans_helper.TRANS_MAGIC in body:
                has_translated_by_gpt = True
                logger.info(f"Already translated, skip")
                return has_translated_by_gpt
            body_trans, body_trans_by_gpt, real_translated = trans_helper.gpt_translate(body)
            if real_translated:
                logger.info(f"Thread: {delivery}: Body:\n{body_trans}\n")
                try:
                    github_helper.update_issue_comment(node_id, trans_helper.wrap_magic(body_trans, original_body=body))
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
            result = trans_discussion(html_url)
    elif event == 'discussion_comment':
        if action != 'created':
            logger.info(f"Thread: {delivery}: Ignore action {action}")
        else:
            html_url = data['comment']['html_url']
            discussion_url = data['discussion']['html_url']
            node_id = data['comment']['node_id']
            body = data['comment']['body']
            logger.info(f"Thread: {delivery}: Got a comment {html_url} of {discussion_url} {node_id} {body}")
            if trans_helper.TRANS_MAGIC in body:
                has_translated_by_gpt = True
                logger.info(f"Already translated, skip")
                return has_translated_by_gpt
            body_trans, body_trans_by_gpt, real_translated = trans_helper.gpt_translate(body)
            if real_translated:
                logger.info(f"Thread: {delivery}: Body:\n{body_trans}\n")
                try:
                    github_helper.update_discussion_comment(node_id, trans_helper.wrap_magic(body_trans, original_body=body))
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
            result = trans_pr(html_url)
    elif event == 'pull_request_review':
        if action != 'submitted':
            logger.info(f"Thread: {delivery}: Ignore action {action}")
        else:
            html_url = data['review']['html_url']
            pull_request_url = data['pull_request']['html_url']
            node_id = data['review']['node_id']
            body = data['review']['body']
            logger.info(f"Thread: {delivery}: Got a PR review {html_url} of {pull_request_url} {node_id} {body}")
            body_trans, body_trans_by_gpt, real_translated = trans_helper.gpt_translate(body)

            if real_translated:
                logger.info(f"Thread: {delivery}: Body:\n{body_trans}\n")
                try:
                    github_helper.update_pullrequest_review(node_id, trans_helper.wrap_magic(body_trans, original_body=body))
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
            logger.info(f"Thread: {delivery}: PR review comments received {html_url} of {pull_request_url} {node_id} {body}")
            body_trans, body_trans_by_gpt, real_translated = trans_helper.gpt_translate(body)
            if real_translated:
                logger.info(f"Thread: {delivery}: Body:\n{body_trans}\n")
                try:
                    github_helper.update_pullrequest_review_comment(node_id, trans_helper.wrap_magic(body_trans, original_body=body))
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
