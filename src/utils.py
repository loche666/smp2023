# -*- coding: utf-8 -*-
# @File    : utils.py
# @Time    : 2023/8/1 上午10:02
# @Author  : xinxin.wang@valueonline
import json
import os

from tqdm import tqdm


def read_json_line(path):
    data = open(path, 'r', encoding='utf-8').readlines()
    if data:
        data = [json.loads(line.strip())['question'] for line in data]
    return data


def get_stopwords(lang_id):
    multi_stopwords = json.load(open('../data/multi_stopwords.json'))
    return multi_stopwords[lang_id]


def rename_files(path):
    """
    train_data 重命名 方便找文件
    :param path:
    :return:
    """
    files = os.listdir(path)
    for f in tqdm(files):
        new_name = f.split('__')
        os.rename(f"{path}/{f}", f"{path}/{new_name[2]}_{new_name[4].strip('年')}.txt")
