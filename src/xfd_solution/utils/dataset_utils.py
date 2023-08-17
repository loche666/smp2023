# -*- coding: utf-8 -*-
# @Desc   : Description of File
# @Licence: (C) Copyright for ValueOnline
# @Author : chen.long
# @Date   : 2023/7/31
import json
import os
from typing import List

from src.xfd_solution.constants.constants import DATA_PATH


def load_jsonl_data(path: str) -> List:
    """读取JSONLF格式数据，以列表返回
    :return:
    """
    datas = []
    with open(path, 'r', encoding='utf-8') as lines:
        for line in lines:
            datas.append(json.loads(line))
    return datas


def save_answers(answers: List, fname: str):
    """将生成的答案保存成JSONl格式
    :return:
    """
    with open(os.path.join(DATA_PATH, fname), 'w', encoding='utf-8') as answer_data:
        for answer in answers:
            answer_data.write(f'{json.dumps(answer, ensure_ascii=False)}\n')


def save_analysis(analysis: List, fname: str):
    """将中间结果保存成JSON格式
    :return:
    """
    with open(os.path.join(DATA_PATH, fname), 'w', encoding='utf-8') as analysis_data:
        json.dump(analysis, analysis_data, ensure_ascii=False, indent=2)
