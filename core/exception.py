# -*- coding:utf-8 -*-
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
