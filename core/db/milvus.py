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
from typing import Union, Dict, List, Optional

from pymilvus import MilvusClient, CollectionSchema
from pymilvus.milvus_client import IndexParams

from core.log import logger
from core.thread import get_backend_thread_pool
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
        self.executor = get_backend_thread_pool()

    async def get_client(self, collection_name):
        if not self.client:
            async with self.init_lock:
                if not self.client:
                    self.client = MilvusClient(uri=self.uri, token=self.token)
                    if self.uri == "sqlite://:memory:":
                        logger.info("Using Milvus in embedded mode (in-memory)")
                    else:
                        logger.info(f"Connected to Milvus server at {self.uri}")

        if collection_name not in self.loaded_collections:
            if collection_name not in self.collection_locks:
                self.collection_locks[collection_name] = asyncio.Lock()

            async with self.collection_locks[collection_name]:
                if collection_name not in self.loaded_collections:
                    try:
                        await self.executor.run_in_thread(self.client.load_collection, collection_name)
                        self.loaded_collections.add(collection_name)
                        logger.info(f"Collection {collection_name} loaded")
                    except Exception as e:
                        logger.error(f"Error loading collection {collection_name}: {e}")

        return self.client

    async def insert(self, collection_name: str, data: Union[Dict, List[Dict]]) -> Dict:
        client = await self.get_client(collection_name)
        return await self.executor.run_in_thread(client.insert, collection_name, data)

    async def delete(self, collection_name: str, ids: Optional[Union[list, str, int]] = None,
                     timeout: Optional[float] = None, filter: Optional[str] = "", ) -> Dict:
        client = await self.get_client(collection_name)
        return await self.executor.run_in_thread(client.delete, collection_name, ids, timeout, filter)

    async def search(self, collection_name: str,
                     data: Union[List[list], list],
                     filter: str = "",
                     limit: int = 10,
                     output_fields: Optional[List[str]] = None,
                     search_params: Optional[dict] = None,
                     timeout: Optional[float] = None,
                     partition_names: Optional[List[str]] = None,
                     anns_field: Optional[str] = None,
                     **kwargs) -> List[List[dict]]:
        client = await self.get_client(collection_name)
        return await self.executor.run_in_thread(client.search, collection_name, data, filter, limit, output_fields,
                                                 search_params, timeout, partition_names, anns_field, **kwargs)

    async def query(self, collection_name: str,
                    filter: str = "",
                    output_fields: Optional[List[str]] = None,
                    timeout: Optional[float] = None,
                    ids: Optional[Union[List, str, int]] = None,
                    partition_names: Optional[List[str]] = None,
                    **kwargs) -> List[dict]:
        client = await self.get_client(collection_name)
        return await self.executor.run_in_thread(client.query, collection_name, filter, output_fields, timeout, ids,
                                                 partition_names, **kwargs)

    async def has_collection(self, collection_name: str, timeout: Optional[float] = None, **kwargs):
        client = await self.get_client(collection_name)
        return await self.executor.run_in_thread(client.has_collection, collection_name, timeout, **kwargs)

    async def create_collection(
            self,
            collection_name: str,
            dimension: Optional[int] = None,
            primary_field_name: str = "id",  # default is "id"
            id_type: str = "int",  # or "string",
            vector_field_name: str = "vector",  # default is  "vector"
            metric_type: str = "COSINE",
            auto_id: bool = False,
            timeout: Optional[float] = None,
            schema: Optional[CollectionSchema] = None,
            index_params: Optional[IndexParams] = None,
            **kwargs,
    ):
        client = await self.get_client(collection_name)
        return await self.executor.run_in_thread(
            client.create_collection,
            collection_name,
            dimension,
            primary_field_name,
            id_type,
            vector_field_name,
            metric_type,
            auto_id,
            timeout,
            schema,
            index_params,
            **kwargs,
        )

    async def create_index(self, collection_name: str, index_params: IndexParams,
                           timeout: Optional[float] = None, **kwargs):
        client = await self.get_client(collection_name)
        return await self.executor.run_in_thread(
            client.create_index,
            collection_name,
            index_params,
            timeout,
            **kwargs,
        )

    async def drop_collection(self, collection_name: str, timeout: Optional[float] = None, **kwargs):
        client = await self.get_client(collection_name)
        return await self.executor.run_in_thread(client.drop_collection, collection_name, timeout, **kwargs)

    async def load_collection(self, collection_name: str, timeout: Optional[float] = None, **kwargs):
        client = await self.get_client(collection_name)
        return await self.executor.run_in_thread(client.load_collection, collection_name, timeout, **kwargs)

    async def refresh_load(self, collection_name: str, timeout: Optional[float] = None, **kwargs):
        client = await self.get_client(collection_name)
        return await self.executor.run_in_thread(client.refresh_load, collection_name, timeout, **kwargs)

    async def release_client(self):
        if self.client:
            try:
                await self.executor.run_in_thread(self.client.close)
                self.loaded_collections.clear()
                logger.info("Milvus client closed")
            except Exception as e:
                logger.error(f"Error closing Milvus client: {e}")
            finally:
                self.client = None

    async def release_all(self):
        async def release_collection(collection):
            try:
                await self.executor.run_in_thread(self.client.release_collection, collection)
                logger.info(f"Collection {collection} released")
            except Exception as e:
                logger.error(f"Error releasing collection {collection}: {e}")

        if self.client:
            await asyncio.gather(*[release_collection(col) for col in self.loaded_collections])
        self.loaded_collections.clear()
        self.collection_locks.clear()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release_client()
        self.executor.shutdown(wait=True)
