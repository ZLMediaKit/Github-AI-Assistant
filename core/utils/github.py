# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
__author__ = 'alex'

import base64
import hashlib
import hmac
from typing import Optional
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel

from core import settings
from core.exception import GithubGraphQLException
from core.models import IssueDetail, DiscussionDetail, PullRequestDetail, Label

ALLOWED_EVENTS = ['pull_request', 'pull_request_review', 'pull_request_review_comment', 'issues', 'issue_comment',
                  'discussion', 'discussion_comment', 'commit_comment']
LABEL_TRANS = Label(name="TransByAI", color="bfdadc", description="Translated by AI", id="")
LABEL_REFINED = Label(name="RefinedByAI", color="f29513", description="Refined by AI", id="")
LABEL_ENGLISH_NATIVE = Label(name="EnglishNative", color="C3A138", description="English Native", id="")
IGNORE_LOGIN = 'dependabot'
GITHUB_REST_API = "https://api.github.com"


class RepoDetail(BaseModel):
    url: str
    owner: str
    name: str
    number: Optional[int] = 0


def get_graphql_headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.get_github_token()}",
        "X-Github-Next-Global-ID": "1",
    }


def get_rest_headers() -> dict:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {settings.get_github_token()}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ZLMediaKit",
    }


def get_github_rest_api_endpoint(path: str) -> str:
    return f"{GITHUB_REST_API}{path}"


def parse_repository_url(url: str) -> RepoDetail:
    """
    :param url: GitHub repository URL, for example, https://github.com/your-org/your-repository
    """
    parsed_url = urlparse(url)
    url_path_list = parsed_url.path.strip('/').split('/')
    repo_model = RepoDetail(url=url, owner=url_path_list[0], name=url_path_list[1])
    return repo_model


def parse_issue_url(url: str) -> RepoDetail:
    """
    :param url: GitHub issue URL, for example, https://github.com/your-org/your-repository/issues/1
    """
    parsed_url = urlparse(url)
    url_path_list = parsed_url.path.strip('/').split('/')
    return RepoDetail(url=url, owner=url_path_list[0], name=url_path_list[1], number=int(url_path_list[3]))


def parse_discussion_url(url: str) -> RepoDetail:
    """
    :param url: GitHub issue URL, for example, https://github.com/your-org/your-repository/discussions/4421
    """
    return parse_issue_url(url)


def parse_pullrequest_url(url: str) -> RepoDetail:
    """
    :param url: GitHub PullRequest URL, for example, https://github.com/your-org/your-repository/pull/3699
    """
    return parse_issue_url(url)


def parse_commit_url(url: str) -> RepoDetail:
    """
    :param url: GitHub PullRequest URL, for example, https://github.com/ZLMediaKit/Github-AI-Assistant/commit/8547b7710226e80589e46570c546d8803b345647
    """
    parsed_url = urlparse(url)
    url_path_list = parsed_url.path.strip('/').split('/')
    return RepoDetail(url=url, owner=url_path_list[0], name=url_path_list[1])


def parse_commit_comment_url(url: str) -> RepoDetail:
    """
    :param url: GitHub commit comment URL, for example,https://api.github.com/repos/ZLMediaKit/translation_issues/comments/146478510
    :param url:
    :return:
    """
    parsed_url = urlparse(url)
    url_path_list = parsed_url.path.strip('/').split('/')
    return RepoDetail(url=url, owner=url_path_list[1], name=url_path_list[2], number=int(url_path_list[4]))


async def do_post_requests(json_data):
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post('https://api.github.com/graphql',
                                     json=json_data,
                                     headers=get_graphql_headers())
        if response.status_code != 200:
            raise Exception(f"request failed, code={response.status_code}")
        result = response.json()
        if 'errors' in result:
            raise GithubGraphQLException(f"request failed, {result}", response)
        return result


async def do_rest_path_requests(path, json_data):
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.patch(get_github_rest_api_endpoint(path),
                                      json=json_data,
                                      headers=get_rest_headers())
        if response.status_code != 200:
            raise Exception(f"request failed, code={response.status_code}, text={response.text}")
        result = response.json()
        return result


async def do_rest_post_requests(path, json_data, http_client: httpx.AsyncClient = None):
    if http_client:
        response = await http_client.post(get_github_rest_api_endpoint(path),
                                          json=json_data,
                                          headers=get_rest_headers())
        if response.status_code != 201:
            raise Exception(f"request failed, code={response.status_code}, text={response.text}")
        result = response.json()
        return result
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(get_github_rest_api_endpoint(path),
                                     json=json_data,
                                     headers=get_rest_headers())
        if response.status_code != 201:
            raise Exception(f"request failed, code={response.status_code}, text={response.text}")
        result = response.json()
        return result


async def do_rest_get_requests(path, http_client: httpx.AsyncClient = None):
    if http_client:
        response = await http_client.get(get_github_rest_api_endpoint(path), headers=get_rest_headers())
        if response.status_code != 200:
            raise Exception(f"request failed, code={response.status_code}, text={response.text}")
        return response.json()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(get_github_rest_api_endpoint(path), headers=get_rest_headers())
        if response.status_code != 200:
            raise Exception(f"request failed, code={response.status_code}, text={response.text}")
        return response.json()


async def get_commit(repo_name: str, commit_sha: str, http_client: httpx.AsyncClient = None) -> dict:
    path = f"/repos/{repo_name}/commits/{commit_sha}"
    return await do_rest_get_requests(path, http_client)


async def get_file_content(repo_name: str, file_path: str, ref: str, http_client: httpx.AsyncClient = None) -> str:
    path = f"/repos/{repo_name}/contents/{file_path}?ref={ref}"
    content_data = await do_rest_get_requests(path, http_client)
    return base64.b64decode(content_data['content']).decode('utf-8')


async def get_pr_files(repo_name: str, pr_number: int, http_client: httpx.AsyncClient = None) -> list:
    path = f"/repos/{repo_name}/pulls/{pr_number}/files"
    return await do_rest_get_requests(path, http_client)


async def query_issue(repo_model: RepoDetail) -> IssueDetail:
    query = '''
        query ($owner: String!, $name: String!, $number: Int!) {
          repository(name: $name, owner: $owner) {
            issue(number: $number) {
              id
              title
              body
              labels(first: 100) {
                totalCount
                nodes {
                  id
                  name
                }
              }
              comments(first: 100) {
                totalCount
                nodes {
                  id
                  author {
                    login
                  }
                  url
                  body
                }
              }
            }
          }
        }
    '''

    result = await do_post_requests({"query": query, "variables": repo_model.dict()})

    total_labels = result['data']['repository']['issue']['labels']['totalCount']
    if total_labels > 100:
        raise Exception(f"too many labels, count={total_labels} {result}")

    total_comments = result['data']['repository']['issue']['comments']['totalCount']
    if total_comments > 100:
        raise Exception(f"too many comments, count={total_comments} {result}")

    # See https://github.com/ghost
    for c in result['data']['repository']['issue']['comments']['nodes']:
        if 'author' not in c or c['author'] is None:
            c['author'] = {'login': 'ghost'}

    result_data = {
        'id': result['data']['repository']['issue']['id'],
        'title': result['data']['repository']['issue']['title'],
        'body': result['data']['repository']['issue']['body'],
        'labels': result['data']['repository']['issue']['labels']['nodes'],
        "comments": result['data']['repository']['issue']['comments']['nodes'],
        "url": repo_model.url
    }
    return IssueDetail(**result_data)


async def query_discussion(repo_model: RepoDetail) -> DiscussionDetail:
    query = '''
        query($name: String!, $owner: String!, $number: Int!) {
          repository(name: $name, owner: $owner) {
            discussion(number: $number) {
              id
              body
              title
              number
              labels(first: 100) {
                totalCount
                nodes {
                  id
                  name
                }
              }
              comments(first: 100) {
                totalCount
                nodes {
                  id
                  author {
                    login
                  }
                  url
                  body
                  replies(first: 100) {
                    totalCount
                    nodes {
                      id
                      author {
                        login
                      }
                      url
                      body
                    }
                    pageInfo {
                      endCursor
                      startCursor
                    }
                  }
                }
                pageInfo {
                  endCursor
                  startCursor
                }
              }
            }
          }
        }
    '''
    result = await do_post_requests({"query": query, "variables": repo_model.dict()})
    total_count = result['data']['repository']['discussion']['comments']['totalCount']
    if total_count > 100:
        raise Exception(f"comments.totalCount > 100, {total_count} of {result}")

    total_count = result['data']['repository']['discussion']["labels"]['totalCount']
    if total_count > 100:
        raise Exception(f"labels.totalCount > 100, {total_count} of {result}")

    j_nodes = result['data']['repository']['discussion']['comments']['nodes']
    for index, j_node in enumerate(j_nodes):
        total_count = j_node["replies"]["totalCount"]
        if total_count > 100:
            raise Exception(f"comments[{index}].replies.totalCount > 100, {total_count} of {j_node}")

    # See https://github.com/ghost
    for c in result['data']['repository']['discussion']['comments']['nodes']:
        if 'author' not in c or c['author'] is None:
            c['author'] = {'login': 'ghost'}
        for r in c['replies']['nodes']:
            if r['author'] is None:
                r['author'] = {'login': 'ghost'}

    result_data = {
        'id': result['data']['repository']['discussion']['id'],
        'title': result['data']['repository']['discussion']['title'],
        'body': result['data']['repository']['discussion']['body'],
        'labels': result['data']['repository']['discussion']['labels']['nodes'],
        "comments": result['data']['repository']['discussion']['comments']['nodes'],
        "url": repo_model.url
    }
    return DiscussionDetail(**result_data)


async def update_issue_comment(issues_id, body):
    query = '''
        mutation ($id: ID!, $body:String!) {
          updateIssueComment(input: {id: $id, body: $body}) {
            issueComment {
              id
            }
          }
        }
    '''
    result = await do_post_requests({"query": query, "variables": {
        "id": issues_id, "body": body,
    }})
    return result['data']['updateIssueComment']['issueComment']['id']


async def update_discussion_comment(discussion_id, body):
    query = '''
        mutation ($id: ID!, $body: String!) {
          updateDiscussionComment(
            input: {commentId: $id, body: $body}
          ) {
            comment {
              id
            }
          }
        }
    '''
    variables = {
        "id": discussion_id,
        'body': body,
    }
    result = await do_post_requests({
        "query": query, "variables": variables
    })
    return result['data']['updateDiscussionComment']['comment']['id']


async def update_issue(issues_id, title, body, original_title=None):
    if original_title:
        title = f"{title}[{original_title}]"
    query = '''
        mutation ($id: ID!, $title:String!, $body: String!) {
          updateIssue(input: {id: $id, body: $body, title: $title}) {
            issue {
              id
            }
          }
        }
    '''
    result = await do_post_requests({"query": query, "variables": {
        "id": issues_id, "title": title, "body": body,
    }})
    return result['data']['updateIssue']['issue']['id']


async def update_discussion(discussion_id, title, body, original_title=None):
    if original_title:
        title = f"{title}[{original_title}]"
    query = '''
        mutation ($id: ID!, $title: String!, $body: String!) {
          updateDiscussion(
            input: {discussionId: $id, title: $title, body: $body}
          ) {
            discussion {
              id
            }
          }
        }
    '''

    result = await do_post_requests({"query": query, "variables": {
        "id": discussion_id,
        "title": title,
        'body': body,
    }})
    return result['data']['updateDiscussion']['discussion']['id']


async def add_label(owner_id, label_id):
    query = '''
        mutation ($id: ID!, $labelIds: [ID!]!) {
          addLabelsToLabelable(
            input: {labelableId: $id, labelIds: $labelIds}
          ) {
            labelable {
              labels {
                totalCount
              }
            }
          }
        }
    '''

    result = await do_post_requests({"query": query, "variables": {
        "id": owner_id, "labelIds": [label_id]
    }})
    return result['data']['addLabelsToLabelable']['labelable']['labels']['totalCount']


async def query_label_id(owner, name, label):
    query = '''
        query($name: String!, $owner: String!, $label: String!) {
          repository(name: $name, owner: $owner) {
            label(name: $label) {
              id
            }
          }
        }
    '''

    result = await do_post_requests({"query": query, "variables": {"name": name, "owner": owner, "label": label}})
    try:
        label_id = result['data']['repository']['label']['id']
        return label_id
    except Exception:
        return None


async def query_pullrequest_all_in_one(repo_model: RepoDetail) -> PullRequestDetail:
    query = '''
        query ($name: String!, $owner: String!, $number: Int!) {
          repository(name: $name, owner: $owner) {
            pullRequest(number: $number) {
              id
              title
              body
              labels(first: 100) {
                totalCount
                nodes {
                  id
                  name
                }
              }
              comments(first: 100) {
                totalCount
                nodes {
                  id
                  url
                  body
                }
              }
              reviews(first: 100) {
                totalCount
                nodes {
                  id
                  url
                  body
                  comments(first: 100) {
                    totalCount
                    nodes {
                      id
                      url
                      body
                    }
                  }
                }
              }
            }
          }
        }
    '''

    result = await do_post_requests({"query": query, "variables": repo_model.dict()})
    total_labels = result['data']['repository']['pullRequest']['labels']['totalCount']
    if total_labels > 100:
        raise Exception(f"too many labels, count={total_labels} {result}")

    total_comments = result['data']['repository']['pullRequest']['comments']['totalCount']
    if total_comments > 100:
        raise Exception(f"too many comments, count={total_comments} {result}")

    total_reviews = result['data']['repository']['pullRequest']['reviews']['totalCount']
    if total_reviews > 100:
        raise Exception(f"too many reviews, count={total_reviews} {result}")

    for review in result['data']['repository']['pullRequest']['reviews']['nodes']:
        total_review_comments = review['comments']['totalCount']
        if total_review_comments > 100:
            raise Exception(f"too many review comments, count={total_review_comments} {result}")

    result_data = {
        "id": result['data']['repository']['pullRequest']['id'],
        "title": result['data']['repository']['pullRequest']['title'],
        "body": result['data']['repository']['pullRequest']['body'],
        "labels": result['data']['repository']['pullRequest']["labels"]["nodes"],
        "comments": result['data']['repository']['pullRequest']["comments"]["nodes"],
        "reviews": result['data']['repository']['pullRequest']['reviews']['nodes'],
        "url": repo_model.url
    }
    return PullRequestDetail(**result_data)


async def update_pullrequest_review(pr_id, body):
    query = '''
        mutation ($id: ID!, $body: String!) {
          updatePullRequestReview(
            input: {pullRequestReviewId: $id, body: $body}
          ) {
            pullRequestReview {
              id
            }
          }
        }
    '''
    variables = {
        "id": pr_id,
        'body': body,
    }
    result = await do_post_requests({
        "query": query, "variables": variables
    })
    return result['data']['updatePullRequestReview']['pullRequestReview']['id']


async def update_pullrequest_review_comment(pr_id, body):
    query = '''
        mutation ($id: ID!, $body: String!) {
          updatePullRequestReviewComment(
            input: {pullRequestReviewCommentId: $id, body: $body}
          ) {
            pullRequestReviewComment {
              id
            }
          }
        }
    '''
    variables = {
        "id": pr_id,
        'body': body,
    }
    result = await do_post_requests({
        "query": query, "variables": variables
    })
    return result['data']['updatePullRequestReviewComment']['pullRequestReviewComment']['id']


async def update_commit_comment(repo_name, comment_id, body):
    path = "/repos/{repo_name}/comments/{comment_id}"
    data = {
        'body': body,
    }

    result = await do_rest_path_requests(path.format(repo_name=repo_name,
                                                     comment_id=comment_id), data)
    return result['body'] == body


async def create_commit_comment(repo_name: str, commit_id: str, body: str, http_client: httpx.AsyncClient = None):
    """
    /repos/{owner}/{repo}/commits/{commit_sha}/comments
    :param http_client:
    :param repo_name:
    :param commit_id:
    :param body:
    :return:
    """
    path = f"/repos/{repo_name}/commits/{commit_id}/comments"
    data = {
        'body': body,
    }
    return await do_rest_post_requests(path, data, http_client)


async def create_pr_comment(repo_name: str, pr_number: int, comment_data: dict, http_client: httpx.AsyncClient = None):
    """
    /repos/{repo_name}/pulls/{pr_number}/comments"
    :param http_client:
    :param repo_name:
    :param pr_number:
    :param comment_data:
    :return:
    """
    path = f"/repos/{repo_name}/pulls/{pr_number}/comments"
    return await do_rest_post_requests(path, comment_data, http_client)


async def update_pullrequest(pr_id, title, body, original_title=None):
    if original_title:
        title = f"{title}[{original_title}]"
    query = '''
        mutation ($id: ID!, $title: String!, $body: String!) {
          updatePullRequest(
            input: {pullRequestId: $id, title: $title, body: $body}
          ) {
            pullRequest {
              id
            }
          }
        }
    '''
    result = await do_post_requests({"query": query, "variables": {
        "id": pr_id, "title": title, "body": body
    }})
    return result['data']['updatePullRequest']['pullRequest']['id']


async def query_pullrequest(owner, name, pr_number):
    query = '''
        query ($name: String!, $owner: String!, $number: Int!) {
          repository(name: $name, owner: $owner) {
            pullRequest(number: $number) {
              id
              title
              body
              mergeable
              author {
                login
              }
              baseRef {
                name
                repository {
                  name
                  owner {
                    login
                  }
                }
              }
              headRef {
                name
                repository {
                  name
                  owner {
                    login
                  }
                }
              }
              participants(first: 100) {
                totalCount
                nodes {
                  login
                }
              }
              labels(first: 100) {
                totalCount
                nodes {
                  id
                  name
                }
              }
            }
          }
        }
    '''

    result = await do_post_requests({"query": query, "variables": {
        "name": name, "owner": owner, "number": pr_number
    }})

    total_labels = result['data']['repository']['pullRequest']['labels']['totalCount']
    if total_labels > 100:
        raise Exception(f"too many labels, count={total_labels} {result}")

    total_participants = result['data']['repository']['pullRequest']['participants']['totalCount']
    if total_participants > 100:
        raise Exception(f"too many participants, count={total_participants} {result}")

    for c in result['data']['repository']['pullRequest']['participants']['nodes']:
        if 'author' not in c or c['author'] is None:
            c['author'] = {'login': 'ghost'}

    return {
        "id": result['data']['repository']['pullRequest']['id'],
        "title": result['data']['repository']['pullRequest']['title'],
        "body": result['data']['repository']['pullRequest']['body'],
        "mergeable": result['data']['repository']['pullRequest']['mergeable'] == 'MERGEABLE',
        "author": result['data']['repository']['pullRequest']['author']['login'],
        "baseRef": result['data']['repository']['pullRequest']['baseRef'],
        "headRef": result['data']['repository']['pullRequest']['headRef'],
        "participants": result['data']['repository']['pullRequest']['participants']['nodes'],
        "labels": result['data']['repository']['pullRequest']["labels"]["nodes"],
    }


async def search_issues(owner, name, isf, sort, labels, count):
    """
    Search GitHub issues, like https://github.com/your-org/your-repository/issues?q=is:issue+sort:comments-desc+-label:TransByAI+
    :param owner: For example, ossrs
    :param name: For example, srs
    :param isf: For example, is:issue is:pr is:discussion
    :param sort: For example, sort:comments-desc
    :param labels: For example, -label:TransByAI
    """
    query = '''
        query ($query: String!, $type:SearchType!, $first: Int!) {
          search(
            query: $query
            type: $type
            first: $first
          ) {
            nodes {
              ... on Discussion {
                id
                title
                url
                comments {
                  totalCount
                }
              }
              ... on Issue {
                id
                title
                url
                comments {
                  totalCount
                }
              }
              ... on PullRequest {
                id
                title
                url
                comments {
                  totalCount
                }
              }
            }
          }
        }
    '''
    search_type = 'ISSUE'
    if 'discussion' in isf:
        search_type = 'DISCUSSION'
    query_filter = f"repo:{owner}/{name} {isf} {sort} {' '.join(labels)}"
    result = await do_post_requests({"query": query, "variables": {
        "query": query_filter, "type": search_type, "first": count
    }})
    return result['data']['search']['nodes']


async def query_repository_id(owner, name):
    query = '''
        query ($owner: String!, $name: String!) {
          repository(owner: $owner, name: $name) {
            id
          }
        }
    '''
    result = await do_post_requests({"query": query, "variables": {
        "owner": owner, "name": name,
    }})
    repository_id = result['data']['repository']['id']
    return repository_id


async def create_issue(repository_id, title, body):
    query = '''
        mutation ($repositoryId: ID!, $title: String!, $body: String!) {
          createIssue(input: {repositoryId: $repositoryId, title: $title, body: $body}) {
            issue {
              id
              url
            }
          }
        }
    '''
    result = await do_post_requests({"query": query, "variables": {
        "repositoryId": repository_id, "title": title, "body": body,
    }})
    issue_id = result['data']['createIssue']['issue']['id']
    issue_url = result['data']['createIssue']['issue']['url']
    return issue_id, issue_url


async def create_label(repository_id, name, color, description=None) -> str:
    query = '''
        mutation ($repositoryId: ID!, $name: String!, $color: String!, $description: String) {
          createLabel(input: {repositoryId: $repositoryId, name: $name, color: $color, description: $description}) {
            label {
              id
              name
              color
              description
            }
          }
        }
    '''
    variables = {
        "repositoryId": repository_id,
        "name": name,
        "color": color,
        "description": description
    }
    result = await do_post_requests({"query": query, "variables": variables})
    return result['data']['createLabel']['label']['id']


async def get_repo_id(owner: str, name: str) -> str:
    query = '''
        query GetRepoId($owner: String!, $name: String!) {
          repository(owner: $owner, name: $name) {
            id
          }
        }
    '''
    variables = {
        "owner": owner,
        "name": name,
    }
    result = await do_post_requests({"query": query, "variables": variables})
    return result['data']['repository']['id']


async def create_label_with_repo_details(owner: str, name: str, label: Label) -> str:
    repo_id = await get_repo_id(owner, name)
    result = await create_label(repo_id, label.name, label.color, label.description)
    return result


async def create_discussion(repository_id, title, body, category_id):
    query = '''
        mutation ($repositoryId: ID!, $title: String!, $body: String!, $categoryId: ID!) {
          createDiscussion(input: {repositoryId: $repositoryId, title: $title, body: $body, categoryId: $categoryId}) {
            discussion {
              id
              url
            }
          }
        }
    '''
    result = await do_post_requests({"query": query, "variables": {
        "repositoryId": repository_id, "title": title, "body": body, "categoryId": category_id,
    }})
    discussion_id = result['data']['createDiscussion']['discussion']['id']
    discussion_url = result['data']['createDiscussion']['discussion']['url']
    return discussion_id, discussion_url


async def query_category_id(owner, name, category_slug):
    query = '''
        query ($name:String!, $owner: String!, $slug: String!) {
          repository(name: $name, owner: $owner) {
            discussionCategory(slug:$slug) {
                id
            }
          }
        }
    '''
    result = await do_post_requests({"query": query, "variables": {
        "name": name, "owner": owner, "slug": category_slug
    }})
    category_id = result['data']['repository']['discussionCategory']['id']
    return category_id


def verify_signature(payload_body, secret_token, signature_header):
    """Verify that the payload was sent from GitHub by validating SHA256.

    Raise and return 403 if not authorized.

    Args:
        payload_body: original request body to verify (request.body())
        secret_token: GitHub app webhook token (WEBHOOK_SECRET)
        signature_header: header received from GitHub (x-hub-signature-256)
    """
    if not signature_header:
        raise Exception("x-hub-signature-256 header is missing!")
    hash_object = hmac.new(secret_token.encode('utf-8'), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = "sha256=" + hash_object.hexdigest()
    if not hmac.compare_digest(expected_signature, signature_header):
        raise Exception("Request signatures didn't match!")
