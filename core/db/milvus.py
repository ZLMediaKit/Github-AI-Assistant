# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
"""
@author:alex
@date:2024/9/16
@time:下午6:29
"""
__author__ = 'alex'

import asyncio

from pymilvus import MilvusClient

from core.log import logger
from core.utils.decorators import singleton_adv


@singleton_adv
class MilvusManager:
    def __init__(self, uri, token):
        self.client = None
        self.uri = uri
        self.token = token
        self.loaded_collections = set()
        self.collection_locks = {}
        self.init_lock = asyncio.Lock()

    async def get_client(self, collection_name):
        if not self.client:
            async with self.init_lock:
                if not self.client:
                    self.client = MilvusClient(uri=self.uri, token=self.token)
                    if self.uri == "sqlite://:memory:":
                        print("Using Milvus in embedded mode (in-memory)")
                    else:
                        print(f"Connected to Milvus server at {self.uri}")
        if collection_name not in self.loaded_collections:
            if collection_name not in self.collection_locks:
                self.collection_locks[collection_name] = asyncio.Lock()

            async with self.collection_locks[collection_name]:
                if collection_name not in self.loaded_collections:
                    try:
                        await asyncio.to_thread(self.client.load_collection, collection_name, None)
                        self.loaded_collections.add(collection_name)
                        logger.info(f"Collection {collection_name} loaded")
                    except Exception as e:
                        logger.error(f"Error loading collection {collection_name}: {e}")
        return self.client

    async def release_client(self):
        if self.client:
            try:
                await asyncio.to_thread(self.client.close)
                self.loaded_collections.clear()
                print("Milvus client closed")
            except Exception as e:
                print(f"Error closing Milvus client: {e}")
            self.client = None

    async def release_all(self):
        async def release_collection(collection):
            try:
                await asyncio.to_thread(self.client.release_collection, collection)
                print(f"Collection {collection} released")
            except Exception as e:
                print(f"Error releasing collection {collection}: {e}")
        if self.client:
            await asyncio.gather(*[release_collection(col) for col in self.loaded_collections])
        self.loaded_collections.clear()
        self.collection_locks.clear()
