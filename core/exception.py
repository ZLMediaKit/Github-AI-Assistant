# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
__author__ = 'alex'


class GithubGraphQLException(Exception):
    def __init__(self, message, res):
        super().__init__(message)
        self.res = res
        self.text = res.text
        self.json = res.json()
        self.errors = None
        if 'errors' in self.json:
            self.errors = self.json['errors']

    def is_forbidden(self):
        if self.errors is not None and len(self.errors) > 0:
            for error in self.errors:
                if 'type' not in error:
                    continue
                # For example: Resource not accessible by personal access token
                if error['type'] == 'FORBIDDEN':
                    return True
                # For example: Cannot be modified since the issue has been converted to a discussion.
                if error['type'] == 'UNPROCESSABLE':
                    return True
        return False


class GithubApiException(Exception):
    def __init__(self, message, response):
        super().__init__(message)
        self.response = response
        self.error_code = -1
        self.error_message = None
