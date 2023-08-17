# -*- coding: utf-8 -*-
# @Desc   : Description of File
# @Licence: (C) Copyright for ValueOnline
# @Author : chen.long
# @Date   : 2023/8/3
import os
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class SimilarityModel:
    def __init__(self, model_path, device='0'):
        os.environ['CUDA_VISIBLE_DEVICES'] = device
        self.model = SentenceTransformer(model_path, device="cuda")

    def encode(self, sentences: List):
        embeddings = self.model.encode(sentences)
        return embeddings

    def range(self, query: str, candidate: List, limit: int) -> List:
        """用于对规则抽取的候选列表进行精拍
        :param query:
        :param candidate:
        :param limit:
        :return:
        """
        tmp_lst = [query]
        tmp_lst.extend([e for e in candidate])
        embeddings = self.encode(tmp_lst)
        query_embedding = np.reshape(embeddings[0], (1, -1))
        cand_embedding = np.reshape(embeddings[1:], (len(candidate), -1))
        similarity = cosine_similarity(query_embedding, cand_embedding)[0]
        limit = limit if limit < len(candidate) else len(candidate)
        indexes = np.argsort(similarity)[-limit:].tolist()
        res = []
        for i, e in enumerate(candidate):
            if i in indexes:
                res.append(e)
        return sorted(res, reverse=True)
