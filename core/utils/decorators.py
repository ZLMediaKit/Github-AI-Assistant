# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
"""
@author:alex
@date:2024/9/15
@time:上午3:28
"""
__author__ = 'alex'

import threading
from collections.abc import Callable
from typing import Generic, ParamSpec, TypeVar, Type, Dict

T = TypeVar("T")
P = ParamSpec("P")


class Singleton(Generic[T, P]):
    """Decorator to create singletons."""

    def __init__(self, cls: Callable[P, T]) -> None:
        self._cls = cls
        self._instance: T | None = None
        self._lock = threading.Lock()

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        with self._lock:
            if self._instance is None:
                self._instance = self._cls(*args, **kwargs)
            return self._instance


class SingletonMeta(type):
    _instances: dict[Type, T] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls: Type[T], *args, **kwargs) -> T:
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]


def singleton_adv(cls: Type[T]) -> Type[T]:
    class SingletonWrapper(cls, metaclass=SingletonMeta):
        pass
    return SingletonWrapper


class SingletonContainer(Generic[T]):
    _instances: Dict[Type[T], T] = {}
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def get_instance(cls, container_class: Type[T], *args, **kwargs) -> T:
        with cls._lock:
            if container_class not in cls._instances:
                instance = container_class(*args, **kwargs)
                cls._instances[container_class] = instance
            return cls._instances[container_class]


def singleton_container(container_class: Type[T]) -> Type[T]:
    class SingletonWrapper(container_class):
        def __new__(cls, *args, **kwargs):
            return SingletonContainer.get_instance(container_class, *args, **kwargs)

    return SingletonWrapper


# 使用示例
@singleton_container
class SingletonDict(dict):
    pass


@singleton_container
class SingletonList(list):
    pass
