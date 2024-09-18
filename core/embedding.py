# -*- coding:utf-8 -*-
#  Copyright (c) 2016-present The ZLMediaKit project authors. All Rights Reserved.
#  This file is part of ZLMediaKit(https://github.com/ZLMediaKit/Github-AI-Assistant).
#  Use of this source code is governed by MIT-like license that can be found in the
#  LICENSE file in the root of the source tree. All contributing project authors
#  may be found in the AUTHORS file in the root of the source tree.
#
"""
@author:alex
@date:2024/9/18
@time:上午1:16
"""
__author__ = 'alex'

import asyncio
import gc
import os
import threading
from typing import List, Generator

import numpy as np
from fastembed import TextEmbedding

from core import settings
from core.log import logger
from core.thread import get_backend_thread_pool
from core.utils.decorators import singleton_adv


@singleton_adv
class EmbeddingModel:
    def __init__(self):
        self.embedding_model = None
        # 线程锁
        self.lock = threading.Lock()
        self.executor = get_backend_thread_pool()

    def load(self):
        with self.lock:
            if self.embedding_model is None:
                local_files_only = True
                logger.info(
                    f"Loading embedding model from {settings.get_embedding_model()}, it may take a few minutes.")
                model_name = f'models--{settings.get_embedding_model().replace("/", "--")}'
                cache_dir = os.path.join(settings.BASE_PATH, './cache')

                if not os.path.exists(os.path.join(cache_dir, model_name)):
                    logger.error(f"Model {settings.get_embedding_model()} not found in the cache directory.")
                    local_files_only = False

                self.embedding_model = TextEmbedding(
                    model_name=settings.get_embedding_model(),
                    cache_dir=cache_dir,
                    local_files_only=local_files_only
                )

    def get_model(self) -> TextEmbedding:
        if self.embedding_model is None:
            self.load()
        return self.embedding_model

    def chunk_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """将文本分割成更小的块"""
        words = text.split()
        return [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]

    def encode_text(self, text: str, chunk_size: int = 1000) -> np.ndarray:
        """
        根据文本大小自适应地选择处理方式
        """
        try:
            model = self.get_model()
            if len(text.split()) <= chunk_size:
                embeddings = next(model.embed([text]))
                return embeddings
            else:
                chunks = self.chunk_text(text, chunk_size)
                embeddings = []
                for chunk in chunks:
                    chunk_embedding = next(model.embed([chunk]))
                    embeddings.append(chunk_embedding)
                    gc.collect()  # Force garbage collection after each chunk
                return np.mean(embeddings, axis=0)
        except Exception as e:
            logger.error(f"Failed to encode text: {e}")
            return np.zeros(model.dim)  # Use the dimension from the model

    def encode_large_document(self, document: str, chunk_size: int = 1000) -> Generator[np.ndarray, None, None]:
        chunks = self.chunk_text(document, chunk_size)
        for chunk in chunks:
            yield self.encode_text(chunk, chunk_size)
            gc.collect()  # Force garbage collection after each chunk

    def process_large_document(self, document: str, chunk_size: int = 1000) -> np.ndarray:
        embeddings = []
        for embedding in self.encode_large_document(document, chunk_size):
            embeddings.append(embedding)
        result = np.mean(embeddings, axis=0)
        del embeddings
        gc.collect()
        return result

    # 异步包装器
    async def async_encode_text(self, text: str, chunk_size: int = 1000) -> np.ndarray:
        return await self.executor.run_in_thread(self.encode_text, text, chunk_size)

    async def async_process_large_document(self, document: str, chunk_size: int = 1000) -> np.ndarray:
        return await self.executor.run_in_thread(self.process_large_document, document, chunk_size)

    def close(self):
        self.executor.shutdown()
