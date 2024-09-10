# -*- coding:utf-8 -*-
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

DETAIL_TYPE_ISSUE = "issues"
DETAIL_TYPE_PR = "pull_request"
DETAIL_TYPE_DISCUSSION = "discussion"
DETAIL_TYPE_COMMIT = "commit"


class Label(BaseModel):
    id: str
    name: str
    color: str = "f29513"
    description: str = None


class Comment(BaseModel):
    id: str
    url: str
    body: str
    author: Optional[dict] = None

    def get_author(self):
        return self.author.get("login", "Unknown")

    def get_detail_text(self):
        text_list = [f"ID: {self.id}", f"Url: {self.url}", f"Author: {self.get_author()}", f"Body:\n{self.body}\n"]
        return "\n".join(text_list)


class Review(BaseModel):
    id: str
    url: str
    body: str
    comments: List[Comment]


class BaseDetail(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    id: str
    title: str
    body: str
    url: str
    labels: List[Label]
    comments: List[Comment]
    model_type_text: str

    def get_detail_text(self):
        text_list = []
        labels_text = ', '.join([f"{label.id}({label.name})" for label in self.labels])
        text_list.append(f"==============={self.model_type_text.upper()}===============")
        text_list.append(f"ID: {self.id}")
        text_list.append(f"Url: {self.url}")
        text_list.append(f"Title: {self.title}")
        text_list.append(f"Labels: {labels_text}")
        text_list.append(f"Body:\n{self.body}\n")
        return "\n".join(text_list)


class IssueDetail(BaseDetail):
    model_type_text: str = DETAIL_TYPE_ISSUE


class DiscussionDetail(BaseDetail):
    model_type_text: str = DETAIL_TYPE_DISCUSSION


class PullRequestDetail(BaseDetail):
    model_type_text: str = DETAIL_TYPE_PR
    reviews: List[Review]


class PullRequest(BaseModel):
    id: str
    title: str
    body: str
    labels: List[Label]
    comments: List[Comment]
    reviews: List[Comment]


class Discussion(BaseModel):
    id: str
    title: str
    body: str
    labels: List[Label]
    comments: List[Comment]
